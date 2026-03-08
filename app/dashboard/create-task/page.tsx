'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Progress } from '@/components/ui/progress';
import { PlatformSelection } from '@/components/task-creation/platform-selection';
import { TaskTypeConfig } from '@/components/task-creation/task-type-config';
import { InstructionEditor } from '@/components/task-creation/instruction-editor';
import { BudgetCalculator } from '@/components/task-creation/budget-calculator';
import { TargetingOptions } from '@/components/task-creation/targeting-options';
import { useTaskWizard } from '@/hooks/use-task-wizard';

export default function CreateTaskPage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const wizard = useTaskWizard();

  const handleSubmit = async () => {
    if (!wizard.isComplete()) {
      console.error('Form validation failed');
      return;
    }

    setIsSubmitting(true);
    try {
      const formData = wizard.getFormData();
      console.log('Submitting task creation form:', formData);

      // TODO: Submit to API
      // const response = await createTask(formData);

      // Clear draft after successful submission
      wizard.clearDraft();

      // Redirect to tasks page or success page
      // router.push('/dashboard/tasks');

      console.log('Task created successfully');
    } catch (error) {
      console.error('Failed to create task:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (confirm('Are you sure you want to cancel? Your progress will be saved as a draft.')) {
      router.push('/dashboard');
    }
  };

  const currentStepId = wizard.steps[wizard.currentStep].id;
  const currentStepErrors = wizard.errors[currentStepId] || {};

  return (
    <div className="min-h-screen bg-gray-50 py-8 dark:bg-gray-900">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Create New Task
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Follow the steps below to create and publish your social media task
          </p>
        </div>

        {/* Progress Indicator */}
        <div className="mb-8">
          <Progress
            steps={wizard.steps}
            currentStep={wizard.currentStep}
            completedSteps={wizard.completedSteps}
          />
        </div>

        {/* Form Content */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800 sm:p-8">
          {/* Step 0: Platform Selection */}
          {wizard.currentStep === 0 && (
            <PlatformSelection
              selectedPlatform={wizard.platformData.platform}
              onSelect={wizard.updatePlatform}
              error={currentStepErrors.platform}
            />
          )}

          {/* Step 1: Task Type Configuration */}
          {wizard.currentStep === 1 && (
            <TaskTypeConfig
              platform={wizard.platformData.platform}
              selectedTaskType={wizard.taskTypeConfig.taskType}
              targetUrl={wizard.taskTypeConfig.targetUrl}
              requirements={wizard.taskTypeConfig.requirements}
              onTaskTypeChange={wizard.updateTaskType}
              onTargetUrlChange={wizard.updateTargetUrl}
              onRequirementsChange={wizard.updateRequirements}
              errors={currentStepErrors}
            />
          )}

          {/* Step 2: Instruction Editor */}
          {wizard.currentStep === 2 && (
            <InstructionEditor
              title={wizard.instructionData.title}
              description={wizard.instructionData.description}
              instructions={wizard.instructionData.instructions}
              onTitleChange={wizard.updateTitle}
              onDescriptionChange={wizard.updateDescription}
              onInstructionsChange={wizard.updateInstructions}
              errors={currentStepErrors}
            />
          )}

          {/* Step 3: Budget Calculator */}
          {wizard.currentStep === 3 && (
            <BudgetCalculator
              taskBudget={wizard.budgetData.taskBudget}
              numberOfTasks={wizard.budgetData.numberOfTasks}
              serviceFee={wizard.budgetData.serviceFee}
              totalCost={wizard.budgetData.totalCost}
              onTaskBudgetChange={wizard.updateTaskBudget}
              onNumberOfTasksChange={wizard.updateNumberOfTasks}
              onServiceFeeChange={wizard.updateServiceFee}
              onTotalCostChange={wizard.updateTotalCost}
              errors={currentStepErrors}
            />
          )}

          {/* Step 4: Targeting Options */}
          {wizard.currentStep === 4 && (
            <TargetingOptions
              targeting={wizard.targetingData}
              onTargetingChange={wizard.updateTargeting}
              errors={currentStepErrors}
            />
          )}

          {/* Navigation Buttons */}
          <div className="mt-8 flex items-center justify-between border-t border-gray-200 pt-6 dark:border-gray-700">
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleCancel}
                disabled={isSubmitting}
                className="rounded-lg border border-gray-300 px-6 py-2 font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              {wizard.canGoPrevious && (
                <button
                  type="button"
                  onClick={wizard.previousStep}
                  disabled={isSubmitting}
                  className="rounded-lg border border-gray-300 px-6 py-2 font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  Previous
                </button>
              )}
            </div>

            <div className="flex items-center gap-3">
              {!wizard.isLastStep && (
                <button
                  type="button"
                  onClick={wizard.nextStep}
                  disabled={isSubmitting}
                  className="rounded-lg bg-primary-500 px-6 py-2 font-medium text-white transition-colors hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next
                </button>
              )}
              {wizard.isLastStep && (
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={isSubmitting}
                  className="rounded-lg bg-green-500 px-6 py-2 font-medium text-white transition-colors hover:bg-green-600 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSubmitting ? 'Creating Task...' : 'Create Task'}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Draft Info */}
        <div className="mt-4 text-center">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Your progress is automatically saved as a draft
          </p>
        </div>
      </div>
    </div>
  );
}
