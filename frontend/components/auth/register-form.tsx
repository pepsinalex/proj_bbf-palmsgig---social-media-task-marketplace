'use client';

import React, { useState, FormEvent } from 'react';
import Link from 'next/link';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { validateRegisterForm, RegisterFormData } from '@/lib/validations/auth';

export interface RegisterFormProps {
  onSubmit?: (data: RegisterFormData) => Promise<void>;
}

export function RegisterForm({ onSubmit }: RegisterFormProps) {
  const [formData, setFormData] = useState<RegisterFormData>({
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
    acceptTerms: false,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
    // Clear error for this field when user types
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
    // Clear server error when user types
    if (serverError) {
      setServerError(null);
    }
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setServerError(null);

    // Validate form
    const validationErrors = validateRegisterForm(formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      if (onSubmit) {
        await onSubmit(formData);
      } else {
        // Default behavior: log to console
        console.log('Register form submitted:', formData);
        // Simulate API call
        await new Promise((resolve) => setTimeout(resolve, 1000));
        window.location.href = '/auth/verify-email';
      }
    } catch (error) {
      console.error('Registration error:', error);
      setServerError(
        error instanceof Error ? error.message : 'An error occurred during registration'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6" noValidate>
      {serverError && (
        <div
          className="rounded-lg bg-red-50 p-4 text-sm text-red-800"
          role="alert"
        >
          {serverError}
        </div>
      )}

      <Input
        type="text"
        name="fullName"
        label="Full Name"
        placeholder="Enter your full name"
        value={formData.fullName}
        onChange={handleChange}
        error={errors.fullName}
        required
        autoComplete="name"
        disabled={isLoading}
      />

      <Input
        type="email"
        name="email"
        label="Email"
        placeholder="Enter your email"
        value={formData.email}
        onChange={handleChange}
        error={errors.email}
        required
        autoComplete="email"
        disabled={isLoading}
      />

      <Input
        type="password"
        name="password"
        label="Password"
        placeholder="Create a password"
        value={formData.password}
        onChange={handleChange}
        error={errors.password}
        required
        autoComplete="new-password"
        disabled={isLoading}
        helperText="Must be at least 8 characters with uppercase, lowercase, and number"
      />

      <Input
        type="password"
        name="confirmPassword"
        label="Confirm Password"
        placeholder="Confirm your password"
        value={formData.confirmPassword}
        onChange={handleChange}
        error={errors.confirmPassword}
        required
        autoComplete="new-password"
        disabled={isLoading}
      />

      <div>
        <label className="flex items-start space-x-3">
          <input
            type="checkbox"
            name="acceptTerms"
            checked={formData.acceptTerms}
            onChange={handleChange}
            disabled={isLoading}
            className="mt-1 h-4 w-4 rounded border-gray-300 text-sky-500 focus:ring-2 focus:ring-sky-500"
          />
          <span className="text-sm text-gray-700">
            I agree to the{' '}
            <Link
              href="/terms"
              className="text-sky-500 hover:text-sky-600 hover:underline"
              target="_blank"
            >
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link
              href="/privacy"
              className="text-sky-500 hover:text-sky-600 hover:underline"
              target="_blank"
            >
              Privacy Policy
            </Link>
          </span>
        </label>
        {errors.acceptTerms && (
          <p className="mt-1.5 text-sm text-red-600" role="alert">
            {errors.acceptTerms}
          </p>
        )}
      </div>

      <Button type="submit" isLoading={isLoading} fullWidth>
        {isLoading ? 'Creating account...' : 'Create account'}
      </Button>

      <p className="text-center text-sm text-gray-600">
        Already have an account?{' '}
        <Link
          href="/auth/login"
          className="font-medium text-sky-500 hover:text-sky-600 hover:underline"
        >
          Sign in
        </Link>
      </p>
    </form>
  );
}
