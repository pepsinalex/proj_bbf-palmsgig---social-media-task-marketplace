'use client';

import { useState, useCallback, useEffect } from 'react';
import type {
  Platform,
  TaskType,
  PlatformSelectionData,
  TaskTypeConfigData,
  InstructionData,
  BudgetData,
  TargetingData,
  TaskCreationFormData,
} from '@/lib/validations/task';
import {
  validatePlatformSelection,
  validateTaskTypeConfig,
  validateInstructionData,
  validateBudgetData,
  validateTargetingData,
} from '@/lib/validations/task';

const DRAFT_STORAGE_KEY = 'task-wizard-draft';

export interface WizardStep {
  id: string;
  label: string;
  description?: string;
}

const WIZARD_STEPS: WizardStep[] = [
  { id: 'platform', label: 'Platform', description: 'Select platform' },
  { id: 'taskType', label: 'Task Type', description: 'Configure task' },
  { id: 'instructions', label: 'Instructions', description: 'Provide details' },
  { id: 'budget', label: 'Budget', description: 'Set pricing' },
  { id: 'targeting', label: 'Targeting', description: 'Define audience' },
];

export function useTaskWizard() {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  // Form state
  const [platformData, setPlatformData] = useState<PlatformSelectionData>({
    platform: null,
  });

  const [taskTypeConfig, setTaskTypeConfig] = useState<TaskTypeConfigData>({
    taskType: null,
    targetUrl: '',
    requirements: [],
  });

  const [instructionData, setInstructionData] = useState<InstructionData>({
    title: '',
    description: '',
    instructions: '',
  });

  const [budgetData, setBudgetData] = useState<BudgetData>({
    taskBudget: 0,
    numberOfTasks: 0,
    serviceFee: 0,
    totalCost: 0,
  });

  const [targetingData, setTargetingData] = useState<TargetingData>({});

  // Validation errors
  const [errors, setErrors] = useState<Record<string, Record<string, string>>>({});

  // Load draft from localStorage on mount
  useEffect(() => {
    try {
      const savedDraft = localStorage.getItem(DRAFT_STORAGE_KEY);
      if (savedDraft) {
        const draft = JSON.parse(savedDraft);
        if (draft.platformData) setPlatformData(draft.platformData);
        if (draft.taskTypeConfig) setTaskTypeConfig(draft.taskTypeConfig);
        if (draft.instructionData) setInstructionData(draft.instructionData);
        if (draft.budgetData) setBudgetData(draft.budgetData);
        if (draft.targetingData) setTargetingData(draft.targetingData);
        if (draft.currentStep !== undefined) setCurrentStep(draft.currentStep);
        if (draft.completedSteps) setCompletedSteps(draft.completedSteps);
        console.log('Loaded task wizard draft from localStorage');
      }
    } catch (error) {
      console.error('Failed to load task wizard draft:', error);
    }
  }, []);

  // Save draft to localStorage whenever form data changes
  const saveDraft = useCallback(() => {
    try {
      const draft = {
        platformData,
        taskTypeConfig,
        instructionData,
        budgetData,
        targetingData,
        currentStep,
        completedSteps,
        savedAt: new Date().toISOString(),
      };
      localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
      console.log('Saved task wizard draft to localStorage');
    } catch (error) {
      console.error('Failed to save task wizard draft:', error);
    }
  }, [platformData, taskTypeConfig, instructionData, budgetData, targetingData, currentStep, completedSteps]);

  // Auto-save draft when form data changes
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      saveDraft();
    }, 1000); // Debounce by 1 second

    return () => clearTimeout(timeoutId);
  }, [saveDraft]);

  // Clear draft
  const clearDraft = useCallback(() => {
    try {
      localStorage.removeItem(DRAFT_STORAGE_KEY);
      console.log('Cleared task wizard draft');
    } catch (error) {
      console.error('Failed to clear task wizard draft:', error);
    }
  }, []);

  // Validate current step
  const validateStep = useCallback(
    (stepIndex: number): boolean => {
      const stepId = WIZARD_STEPS[stepIndex].id;
      let stepErrors: Record<string, string> = {};

      switch (stepId) {
        case 'platform':
          stepErrors = validatePlatformSelection(platformData);
          break;
        case 'taskType':
          stepErrors = validateTaskTypeConfig(taskTypeConfig, platformData.platform);
          break;
        case 'instructions':
          stepErrors = validateInstructionData(instructionData);
          break;
        case 'budget':
          stepErrors = validateBudgetData(budgetData);
          break;
        case 'targeting':
          stepErrors = validateTargetingData(targetingData);
          break;
      }

      if (Object.keys(stepErrors).length > 0) {
        setErrors((prev) => ({ ...prev, [stepId]: stepErrors }));
        return false;
      }

      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[stepId];
        return newErrors;
      });
      return true;
    },
    [platformData, taskTypeConfig, instructionData, budgetData, targetingData]
  );

  // Navigate to next step
  const nextStep = useCallback(() => {
    if (!validateStep(currentStep)) {
      return false;
    }

    if (currentStep < WIZARD_STEPS.length - 1) {
      if (!completedSteps.includes(currentStep)) {
        setCompletedSteps((prev) => [...prev, currentStep]);
      }
      setCurrentStep((prev) => prev + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return true;
    }
    return false;
  }, [currentStep, validateStep, completedSteps]);

  // Navigate to previous step
  const previousStep = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [currentStep]);

  // Go to specific step
  const goToStep = useCallback((stepIndex: number) => {
    if (stepIndex >= 0 && stepIndex < WIZARD_STEPS.length) {
      setCurrentStep(stepIndex);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, []);

  // Check if all steps are completed
  const isComplete = useCallback((): boolean => {
    for (let i = 0; i < WIZARD_STEPS.length; i++) {
      if (!validateStep(i)) {
        return false;
      }
    }
    return true;
  }, [validateStep]);

  // Get form data
  const getFormData = useCallback((): TaskCreationFormData => {
    return {
      platform: platformData,
      taskTypeConfig,
      instruction: instructionData,
      budget: budgetData,
      targeting: targetingData,
    };
  }, [platformData, taskTypeConfig, instructionData, budgetData, targetingData]);

  // Reset wizard
  const reset = useCallback(() => {
    setPlatformData({ platform: null });
    setTaskTypeConfig({ taskType: null, targetUrl: '', requirements: [] });
    setInstructionData({ title: '', description: '', instructions: '' });
    setBudgetData({ taskBudget: 0, numberOfTasks: 0, serviceFee: 0, totalCost: 0 });
    setTargetingData({});
    setCurrentStep(0);
    setCompletedSteps([]);
    setErrors({});
    clearDraft();
  }, [clearDraft]);

  // Update platform data
  const updatePlatform = useCallback((platform: Platform) => {
    setPlatformData({ platform });
  }, []);

  // Update task type config
  const updateTaskType = useCallback((taskType: TaskType) => {
    setTaskTypeConfig((prev) => ({ ...prev, taskType }));
  }, []);

  const updateTargetUrl = useCallback((url: string) => {
    setTaskTypeConfig((prev) => ({ ...prev, targetUrl: url }));
  }, []);

  const updateRequirements = useCallback((requirements: string[]) => {
    setTaskTypeConfig((prev) => ({ ...prev, requirements }));
  }, []);

  // Update instruction data
  const updateTitle = useCallback((title: string) => {
    setInstructionData((prev) => ({ ...prev, title }));
  }, []);

  const updateDescription = useCallback((description: string) => {
    setInstructionData((prev) => ({ ...prev, description }));
  }, []);

  const updateInstructions = useCallback((instructions: string) => {
    setInstructionData((prev) => ({ ...prev, instructions }));
  }, []);

  // Update budget data
  const updateTaskBudget = useCallback((taskBudget: number) => {
    setBudgetData((prev) => ({ ...prev, taskBudget }));
  }, []);

  const updateNumberOfTasks = useCallback((numberOfTasks: number) => {
    setBudgetData((prev) => ({ ...prev, numberOfTasks }));
  }, []);

  const updateServiceFee = useCallback((serviceFee: number) => {
    setBudgetData((prev) => ({ ...prev, serviceFee }));
  }, []);

  const updateTotalCost = useCallback((totalCost: number) => {
    setBudgetData((prev) => ({ ...prev, totalCost }));
  }, []);

  // Update targeting data
  const updateTargeting = useCallback((targeting: TargetingData) => {
    setTargetingData(targeting);
  }, []);

  return {
    // State
    steps: WIZARD_STEPS,
    currentStep,
    completedSteps,
    platformData,
    taskTypeConfig,
    instructionData,
    budgetData,
    targetingData,
    errors,

    // Actions
    nextStep,
    previousStep,
    goToStep,
    validateStep,
    isComplete,
    getFormData,
    reset,
    saveDraft,
    clearDraft,

    // Update functions
    updatePlatform,
    updateTaskType,
    updateTargetUrl,
    updateRequirements,
    updateTitle,
    updateDescription,
    updateInstructions,
    updateTaskBudget,
    updateNumberOfTasks,
    updateServiceFee,
    updateTotalCost,
    updateTargeting,

    // Computed properties
    isFirstStep: currentStep === 0,
    isLastStep: currentStep === WIZARD_STEPS.length - 1,
    canGoNext: currentStep < WIZARD_STEPS.length - 1,
    canGoPrevious: currentStep > 0,
  };
}
