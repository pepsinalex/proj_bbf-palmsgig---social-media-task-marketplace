// Validation schemas for profile and settings forms
// Following the validation pattern from auth.ts

export interface ProfileFormData {
  fullName: string;
  bio?: string;
  profilePicture?: string;
}

export interface SettingsFormData {
  emailNotifications: boolean;
  taskNotifications: boolean;
  marketingEmails: boolean;
  twoFactorEnabled: boolean;
}

// Full name validation
export const validateFullName = (fullName: string): string | null => {
  if (!fullName) {
    return 'Full name is required';
  }
  if (fullName.trim().length < 2) {
    return 'Full name must be at least 2 characters';
  }
  if (fullName.trim().length > 100) {
    return 'Full name must not exceed 100 characters';
  }
  return null;
};

// Bio validation
export const validateBio = (bio?: string): string | null => {
  if (!bio) {
    return null; // Bio is optional
  }
  if (bio.trim().length > 500) {
    return 'Bio must not exceed 500 characters';
  }
  return null;
};

// Profile picture URL validation
export const validateProfilePicture = (profilePicture?: string): string | null => {
  if (!profilePicture) {
    return null; // Profile picture is optional
  }
  try {
    new URL(profilePicture);
    return null;
  } catch {
    return 'Invalid profile picture URL';
  }
};

// Validate profile form
export const validateProfileForm = (data: ProfileFormData): Record<string, string> => {
  const errors: Record<string, string> = {};

  const fullNameError = validateFullName(data.fullName);
  if (fullNameError) {
    errors.fullName = fullNameError;
  }

  const bioError = validateBio(data.bio);
  if (bioError) {
    errors.bio = bioError;
  }

  const profilePictureError = validateProfilePicture(data.profilePicture);
  if (profilePictureError) {
    errors.profilePicture = profilePictureError;
  }

  return errors;
};

// Validate settings form
export const validateSettingsForm = (data: SettingsFormData): Record<string, string> => {
  // Settings form has boolean values, no validation errors expected
  // But we keep the function for consistency with other validation functions
  return {};
};

// Social account username validation
export const validateSocialUsername = (username: string): string | null => {
  if (!username) {
    return 'Username is required';
  }
  if (username.trim().length < 1) {
    return 'Username must not be empty';
  }
  if (username.trim().length > 50) {
    return 'Username must not exceed 50 characters';
  }
  // Check for valid username format (alphanumeric, underscores, dots, hyphens)
  if (!/^[a-zA-Z0-9._-]+$/.test(username)) {
    return 'Username can only contain letters, numbers, dots, underscores, and hyphens';
  }
  return null;
};

// Validate social platform
export const validateSocialPlatform = (
  platform: string | null
): string | null => {
  if (!platform) {
    return 'Platform is required';
  }
  const validPlatforms = ['instagram', 'twitter', 'facebook', 'tiktok', 'youtube'];
  if (!validPlatforms.includes(platform)) {
    return 'Invalid social platform';
  }
  return null;
};
