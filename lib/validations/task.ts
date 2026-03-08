// Validation schemas for task creation form
// Since zod is not available in package.json, implementing basic validation functions

// Platform types
export type Platform = 'instagram' | 'twitter' | 'facebook' | 'tiktok' | 'youtube';

// Task types for each platform
export type InstagramTaskType =
  | 'like'
  | 'comment'
  | 'follow'
  | 'story_view'
  | 'reel_view'
  | 'save'
  | 'share';

export type TwitterTaskType =
  | 'like'
  | 'retweet'
  | 'comment'
  | 'follow'
  | 'quote_tweet'
  | 'bookmark';

export type FacebookTaskType =
  | 'like'
  | 'comment'
  | 'share'
  | 'follow'
  | 'reaction'
  | 'page_like';

export type TikTokTaskType =
  | 'like'
  | 'comment'
  | 'follow'
  | 'share'
  | 'duet'
  | 'stitch'
  | 'favorite';

export type YouTubeTaskType =
  | 'like'
  | 'comment'
  | 'subscribe'
  | 'watch'
  | 'share'
  | 'playlist_add';

export type TaskType =
  | InstagramTaskType
  | TwitterTaskType
  | FacebookTaskType
  | TikTokTaskType
  | YouTubeTaskType;

// Form data interfaces for each step
export interface PlatformSelectionData {
  platform: Platform | null;
}

export interface TaskTypeConfigData {
  taskType: TaskType | null;
  targetUrl: string;
  requirements: string[];
}

export interface InstructionData {
  title: string;
  description: string;
  instructions: string;
}

export interface BudgetData {
  taskBudget: number;
  numberOfTasks: number;
  serviceFee: number;
  totalCost: number;
}

export interface TargetingData {
  minFollowers?: number;
  maxFollowers?: number;
  ageRange?: {
    min: number;
    max: number;
  };
  gender?: 'all' | 'male' | 'female' | 'other';
  countries?: string[];
  interests?: string[];
  languages?: string[];
}

export interface TaskCreationFormData {
  platform: PlatformSelectionData;
  taskTypeConfig: TaskTypeConfigData;
  instruction: InstructionData;
  budget: BudgetData;
  targeting: TargetingData;
}

// Validation functions for platform selection
export const validatePlatform = (platform: Platform | null): string | null => {
  if (!platform) {
    return 'Please select a platform';
  }
  const validPlatforms: Platform[] = ['instagram', 'twitter', 'facebook', 'tiktok', 'youtube'];
  if (!validPlatforms.includes(platform)) {
    return 'Invalid platform selected';
  }
  return null;
};

export const validatePlatformSelection = (
  data: PlatformSelectionData
): Record<string, string> => {
  const errors: Record<string, string> = {};

  const platformError = validatePlatform(data.platform);
  if (platformError) {
    errors.platform = platformError;
  }

  return errors;
};

// Validation functions for task type configuration
export const validateTaskType = (
  taskType: TaskType | null,
  platform: Platform | null
): string | null => {
  if (!taskType) {
    return 'Please select a task type';
  }

  if (!platform) {
    return 'Platform must be selected first';
  }

  // Platform-specific task type validation
  const taskTypesByPlatform: Record<Platform, string[]> = {
    instagram: ['like', 'comment', 'follow', 'story_view', 'reel_view', 'save', 'share'],
    twitter: ['like', 'retweet', 'comment', 'follow', 'quote_tweet', 'bookmark'],
    facebook: ['like', 'comment', 'share', 'follow', 'reaction', 'page_like'],
    tiktok: ['like', 'comment', 'follow', 'share', 'duet', 'stitch', 'favorite'],
    youtube: ['like', 'comment', 'subscribe', 'watch', 'share', 'playlist_add'],
  };

  if (!taskTypesByPlatform[platform].includes(taskType)) {
    return `Invalid task type for ${platform}`;
  }

  return null;
};

export const validateTargetUrl = (url: string, platform: Platform | null): string | null => {
  if (!url) {
    return 'Target URL is required';
  }

  const trimmedUrl = url.trim();
  if (!trimmedUrl) {
    return 'Target URL is required';
  }

  // Basic URL validation
  try {
    const urlObj = new URL(trimmedUrl);
    const hostname = urlObj.hostname.toLowerCase();

    // Platform-specific URL validation
    if (platform) {
      const platformDomains: Record<Platform, string[]> = {
        instagram: ['instagram.com', 'www.instagram.com'],
        twitter: ['twitter.com', 'www.twitter.com', 'x.com', 'www.x.com'],
        facebook: ['facebook.com', 'www.facebook.com', 'fb.com', 'www.fb.com'],
        tiktok: ['tiktok.com', 'www.tiktok.com'],
        youtube: ['youtube.com', 'www.youtube.com', 'youtu.be'],
      };

      const validDomains = platformDomains[platform];
      if (!validDomains.some((domain) => hostname.includes(domain))) {
        return `URL must be a valid ${platform} link`;
      }
    }
  } catch {
    return 'Invalid URL format';
  }

  return null;
};

export const validateRequirements = (requirements: string[]): string | null => {
  if (!requirements || requirements.length === 0) {
    return 'At least one requirement must be specified';
  }

  for (const req of requirements) {
    if (!req || req.trim().length === 0) {
      return 'Requirements cannot be empty';
    }
    if (req.trim().length > 200) {
      return 'Each requirement must be less than 200 characters';
    }
  }

  if (requirements.length > 10) {
    return 'Maximum 10 requirements allowed';
  }

  return null;
};

export const validateTaskTypeConfig = (
  data: TaskTypeConfigData,
  platform: Platform | null
): Record<string, string> => {
  const errors: Record<string, string> = {};

  const taskTypeError = validateTaskType(data.taskType, platform);
  if (taskTypeError) {
    errors.taskType = taskTypeError;
  }

  const targetUrlError = validateTargetUrl(data.targetUrl, platform);
  if (targetUrlError) {
    errors.targetUrl = targetUrlError;
  }

  const requirementsError = validateRequirements(data.requirements);
  if (requirementsError) {
    errors.requirements = requirementsError;
  }

  return errors;
};

// Validation functions for instructions
export const validateTitle = (title: string): string | null => {
  if (!title) {
    return 'Title is required';
  }

  const trimmedTitle = title.trim();
  if (trimmedTitle.length < 5) {
    return 'Title must be at least 5 characters';
  }

  if (trimmedTitle.length > 100) {
    return 'Title must be less than 100 characters';
  }

  return null;
};

export const validateDescription = (description: string): string | null => {
  if (!description) {
    return 'Description is required';
  }

  const trimmedDescription = description.trim();
  if (trimmedDescription.length < 20) {
    return 'Description must be at least 20 characters';
  }

  if (trimmedDescription.length > 500) {
    return 'Description must be less than 500 characters';
  }

  return null;
};

export const validateInstructions = (instructions: string): string | null => {
  if (!instructions) {
    return 'Instructions are required';
  }

  const trimmedInstructions = instructions.trim();
  if (trimmedInstructions.length < 50) {
    return 'Instructions must be at least 50 characters';
  }

  if (trimmedInstructions.length > 2000) {
    return 'Instructions must be less than 2000 characters';
  }

  return null;
};

export const validateInstructionData = (data: InstructionData): Record<string, string> => {
  const errors: Record<string, string> = {};

  const titleError = validateTitle(data.title);
  if (titleError) {
    errors.title = titleError;
  }

  const descriptionError = validateDescription(data.description);
  if (descriptionError) {
    errors.description = descriptionError;
  }

  const instructionsError = validateInstructions(data.instructions);
  if (instructionsError) {
    errors.instructions = instructionsError;
  }

  return errors;
};

// Validation functions for budget
export const validateTaskBudget = (taskBudget: number): string | null => {
  if (taskBudget === null || taskBudget === undefined || isNaN(taskBudget)) {
    return 'Task budget is required';
  }

  if (taskBudget <= 0) {
    return 'Task budget must be greater than 0';
  }

  if (taskBudget < 0.5) {
    return 'Minimum task budget is $0.50';
  }

  if (taskBudget > 1000) {
    return 'Maximum task budget is $1000 per task';
  }

  return null;
};

export const validateNumberOfTasks = (numberOfTasks: number): string | null => {
  if (numberOfTasks === null || numberOfTasks === undefined || isNaN(numberOfTasks)) {
    return 'Number of tasks is required';
  }

  if (numberOfTasks <= 0) {
    return 'Number of tasks must be greater than 0';
  }

  if (!Number.isInteger(numberOfTasks)) {
    return 'Number of tasks must be a whole number';
  }

  if (numberOfTasks < 1) {
    return 'Minimum 1 task required';
  }

  if (numberOfTasks > 10000) {
    return 'Maximum 10,000 tasks allowed';
  }

  return null;
};

export const calculateServiceFee = (taskBudget: number, numberOfTasks: number): number => {
  const subtotal = taskBudget * numberOfTasks;
  return subtotal * 0.15; // 15% service fee
};

export const calculateTotalCost = (taskBudget: number, numberOfTasks: number): number => {
  const subtotal = taskBudget * numberOfTasks;
  const serviceFee = calculateServiceFee(taskBudget, numberOfTasks);
  return subtotal + serviceFee;
};

export const validateBudgetData = (data: BudgetData): Record<string, string> => {
  const errors: Record<string, string> = {};

  const taskBudgetError = validateTaskBudget(data.taskBudget);
  if (taskBudgetError) {
    errors.taskBudget = taskBudgetError;
  }

  const numberOfTasksError = validateNumberOfTasks(data.numberOfTasks);
  if (numberOfTasksError) {
    errors.numberOfTasks = numberOfTasksError;
  }

  // Validate service fee calculation
  if (!taskBudgetError && !numberOfTasksError) {
    const expectedServiceFee = calculateServiceFee(data.taskBudget, data.numberOfTasks);
    const expectedTotalCost = calculateTotalCost(data.taskBudget, data.numberOfTasks);

    if (Math.abs(data.serviceFee - expectedServiceFee) > 0.01) {
      errors.serviceFee = 'Service fee calculation is incorrect';
    }

    if (Math.abs(data.totalCost - expectedTotalCost) > 0.01) {
      errors.totalCost = 'Total cost calculation is incorrect';
    }
  }

  return errors;
};

// Validation functions for targeting options
export const validateFollowerRange = (
  minFollowers?: number,
  maxFollowers?: number
): string | null => {
  if (minFollowers !== undefined && minFollowers !== null) {
    if (minFollowers < 0) {
      return 'Minimum followers cannot be negative';
    }
    if (!Number.isInteger(minFollowers)) {
      return 'Minimum followers must be a whole number';
    }
  }

  if (maxFollowers !== undefined && maxFollowers !== null) {
    if (maxFollowers < 0) {
      return 'Maximum followers cannot be negative';
    }
    if (!Number.isInteger(maxFollowers)) {
      return 'Maximum followers must be a whole number';
    }
  }

  if (
    minFollowers !== undefined &&
    minFollowers !== null &&
    maxFollowers !== undefined &&
    maxFollowers !== null
  ) {
    if (minFollowers > maxFollowers) {
      return 'Minimum followers cannot be greater than maximum followers';
    }
  }

  return null;
};

export const validateAgeRange = (ageRange?: { min: number; max: number }): string | null => {
  if (!ageRange) {
    return null; // Age range is optional
  }

  if (ageRange.min < 13) {
    return 'Minimum age cannot be less than 13';
  }

  if (ageRange.max > 100) {
    return 'Maximum age cannot be greater than 100';
  }

  if (ageRange.min > ageRange.max) {
    return 'Minimum age cannot be greater than maximum age';
  }

  if (!Number.isInteger(ageRange.min) || !Number.isInteger(ageRange.max)) {
    return 'Age values must be whole numbers';
  }

  return null;
};

export const validateGender = (gender?: string): string | null => {
  if (!gender) {
    return null; // Gender is optional
  }

  const validGenders = ['all', 'male', 'female', 'other'];
  if (!validGenders.includes(gender)) {
    return 'Invalid gender selection';
  }

  return null;
};

export const validateCountries = (countries?: string[]): string | null => {
  if (!countries || countries.length === 0) {
    return null; // Countries are optional
  }

  if (countries.length > 50) {
    return 'Maximum 50 countries allowed';
  }

  for (const country of countries) {
    if (!country || country.trim().length === 0) {
      return 'Country names cannot be empty';
    }
    if (country.trim().length > 100) {
      return 'Country name is too long';
    }
  }

  return null;
};

export const validateInterests = (interests?: string[]): string | null => {
  if (!interests || interests.length === 0) {
    return null; // Interests are optional
  }

  if (interests.length > 20) {
    return 'Maximum 20 interests allowed';
  }

  for (const interest of interests) {
    if (!interest || interest.trim().length === 0) {
      return 'Interest names cannot be empty';
    }
    if (interest.trim().length > 50) {
      return 'Interest name is too long';
    }
  }

  return null;
};

export const validateLanguages = (languages?: string[]): string | null => {
  if (!languages || languages.length === 0) {
    return null; // Languages are optional
  }

  if (languages.length > 10) {
    return 'Maximum 10 languages allowed';
  }

  for (const language of languages) {
    if (!language || language.trim().length === 0) {
      return 'Language names cannot be empty';
    }
    if (language.trim().length > 50) {
      return 'Language name is too long';
    }
  }

  return null;
};

export const validateTargetingData = (data: TargetingData): Record<string, string> => {
  const errors: Record<string, string> = {};

  const followerRangeError = validateFollowerRange(data.minFollowers, data.maxFollowers);
  if (followerRangeError) {
    errors.followerRange = followerRangeError;
  }

  const ageRangeError = validateAgeRange(data.ageRange);
  if (ageRangeError) {
    errors.ageRange = ageRangeError;
  }

  const genderError = validateGender(data.gender);
  if (genderError) {
    errors.gender = genderError;
  }

  const countriesError = validateCountries(data.countries);
  if (countriesError) {
    errors.countries = countriesError;
  }

  const interestsError = validateInterests(data.interests);
  if (interestsError) {
    errors.interests = interestsError;
  }

  const languagesError = validateLanguages(data.languages);
  if (languagesError) {
    errors.languages = languagesError;
  }

  return errors;
};

// Complete form validation
export const validateTaskCreationForm = (
  data: TaskCreationFormData
): Record<string, Record<string, string>> => {
  const errors: Record<string, Record<string, string>> = {};

  const platformErrors = validatePlatformSelection(data.platform);
  if (Object.keys(platformErrors).length > 0) {
    errors.platform = platformErrors;
  }

  const taskTypeConfigErrors = validateTaskTypeConfig(data.taskTypeConfig, data.platform.platform);
  if (Object.keys(taskTypeConfigErrors).length > 0) {
    errors.taskTypeConfig = taskTypeConfigErrors;
  }

  const instructionErrors = validateInstructionData(data.instruction);
  if (Object.keys(instructionErrors).length > 0) {
    errors.instruction = instructionErrors;
  }

  const budgetErrors = validateBudgetData(data.budget);
  if (Object.keys(budgetErrors).length > 0) {
    errors.budget = budgetErrors;
  }

  const targetingErrors = validateTargetingData(data.targeting);
  if (Object.keys(targetingErrors).length > 0) {
    errors.targeting = targetingErrors;
  }

  return errors;
};

// Helper function to check if form is valid
export const isTaskCreationFormValid = (data: TaskCreationFormData): boolean => {
  const errors = validateTaskCreationForm(data);
  return Object.keys(errors).length === 0;
};
