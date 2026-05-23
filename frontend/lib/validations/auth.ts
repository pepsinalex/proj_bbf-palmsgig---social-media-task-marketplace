// Validation schemas for authentication forms
// Since zod is not available in package.json, implementing basic validation functions

import { UserRole } from '@/lib/types/api';

export type RegisterRole = UserRole.EMPLOYER | UserRole.EMPLOYEE;

export interface LoginFormData {
  email: string;
  password: string;
}

export interface RegisterFormData {
  email: string;
  password: string;
  confirmPassword: string;
  fullName: string;
  role: RegisterRole | '';
  acceptTerms: boolean;
}

export interface ForgotPasswordFormData {
  email: string;
}

export interface VerifyEmailFormData {
  code: string;
}

export interface VerifyPhoneFormData {
  code: string;
}

// Email validation
export const validateEmail = (email: string): string | null => {
  if (!email) {
    return 'Email is required';
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return 'Invalid email format';
  }
  return null;
};

// Password validation
export const validatePassword = (password: string): string | null => {
  if (!password) {
    return 'Password is required';
  }
  if (password.length < 8) {
    return 'Password must be at least 8 characters';
  }
  if (!/[A-Z]/.test(password)) {
    return 'Password must contain at least one uppercase letter';
  }
  if (!/[a-z]/.test(password)) {
    return 'Password must contain at least one lowercase letter';
  }
  if (!/[0-9]/.test(password)) {
    return 'Password must contain at least one number';
  }
  return null;
};

// Confirm password validation
export const validateConfirmPassword = (
  password: string,
  confirmPassword: string
): string | null => {
  if (!confirmPassword) {
    return 'Please confirm your password';
  }
  if (password !== confirmPassword) {
    return 'Passwords do not match';
  }
  return null;
};

// Full name validation
export const validateFullName = (fullName: string): string | null => {
  if (!fullName) {
    return 'Full name is required';
  }
  if (fullName.trim().length < 2) {
    return 'Full name must be at least 2 characters';
  }
  return null;
};

// Terms acceptance validation
export const validateTermsAcceptance = (accepted: boolean): string | null => {
  if (!accepted) {
    return 'You must accept the terms and conditions';
  }
  return null;
};

// Role validation
// Employer: posts tasks and pays for completed work.
// Employee: completes tasks and earns rewards.
export const validateRole = (role: string | RegisterRole | ''): string | null => {
  if (!role) {
    return 'Please select a role to continue';
  }
  if (role !== UserRole.EMPLOYER && role !== UserRole.EMPLOYEE) {
    return 'Role must be either Employer or Employee';
  }
  return null;
};

// OTP/Code validation
export const validateCode = (code: string): string | null => {
  if (!code) {
    return 'Verification code is required';
  }
  if (!/^\d{6}$/.test(code)) {
    return 'Verification code must be 6 digits';
  }
  return null;
};

// Validate login form
export const validateLoginForm = (data: LoginFormData): Record<string, string> => {
  const errors: Record<string, string> = {};

  const emailError = validateEmail(data.email);
  if (emailError) {
    errors.email = emailError;
  }

  const passwordError = validatePassword(data.password);
  if (passwordError) {
    errors.password = passwordError;
  }

  return errors;
};

// Validate register form
export const validateRegisterForm = (data: RegisterFormData): Record<string, string> => {
  const errors: Record<string, string> = {};

  const emailError = validateEmail(data.email);
  if (emailError) {
    errors.email = emailError;
  }

  const fullNameError = validateFullName(data.fullName);
  if (fullNameError) {
    errors.fullName = fullNameError;
  }

  const passwordError = validatePassword(data.password);
  if (passwordError) {
    errors.password = passwordError;
  }

  const confirmPasswordError = validateConfirmPassword(data.password, data.confirmPassword);
  if (confirmPasswordError) {
    errors.confirmPassword = confirmPasswordError;
  }

  const roleError = validateRole(data.role);
  if (roleError) {
    errors.role = roleError;
  }

  const termsError = validateTermsAcceptance(data.acceptTerms);
  if (termsError) {
    errors.acceptTerms = termsError;
  }

  return errors;
};

// Validate forgot password form
export const validateForgotPasswordForm = (
  data: ForgotPasswordFormData
): Record<string, string> => {
  const errors: Record<string, string> = {};

  const emailError = validateEmail(data.email);
  if (emailError) {
    errors.email = emailError;
  }

  return errors;
};

// Validate verification code form
export const validateVerificationForm = (
  data: VerifyEmailFormData | VerifyPhoneFormData
): Record<string, string> => {
  const errors: Record<string, string> = {};

  const codeError = validateCode(data.code);
  if (codeError) {
    errors.code = codeError;
  }

  return errors;
};
