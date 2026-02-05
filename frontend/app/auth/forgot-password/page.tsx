'use client';

import React, { useState, FormEvent } from 'react';
import Link from 'next/link';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { validateForgotPasswordForm, ForgotPasswordFormData } from '@/lib/validations/auth';

export default function ForgotPasswordPage() {
  const [formData, setFormData] = useState<ForgotPasswordFormData>({
    email: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
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
    setIsSuccess(false);

    // Validate form
    const validationErrors = validateForgotPasswordForm(formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      // Simulate API call
      console.log('Forgot password submitted:', formData);
      await new Promise((resolve) => setTimeout(resolve, 1500));
      setIsSuccess(true);
    } catch (error) {
      console.error('Forgot password error:', error);
      setServerError(
        error instanceof Error
          ? error.message
          : 'An error occurred while sending the reset email'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <Link href="/" className="inline-block">
            <h1 className="text-3xl font-bold text-sky-500">PalmsGig</h1>
          </Link>
          <h2 className="mt-6 text-2xl font-bold text-gray-900">
            Reset your password
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Enter your email and we&apos;ll send you instructions to reset your password
          </p>
        </div>

        <div className="rounded-lg bg-white px-8 py-10 shadow-md">
          {isSuccess ? (
            <div className="space-y-6">
              <div className="rounded-lg bg-green-50 p-4">
                <div className="flex items-center">
                  <svg
                    className="h-5 w-5 text-green-400"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800">
                      Email sent successfully
                    </h3>
                    <div className="mt-2 text-sm text-green-700">
                      <p>
                        We&apos;ve sent password reset instructions to{' '}
                        <span className="font-semibold">{formData.email}</span>. Please check
                        your inbox and follow the link to reset your password.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-3 text-center text-sm">
                <p className="text-gray-600">
                  Didn&apos;t receive the email?{' '}
                  <button
                    onClick={() => setIsSuccess(false)}
                    className="font-medium text-sky-500 hover:text-sky-600 hover:underline"
                  >
                    Try again
                  </button>
                </p>
                <Link
                  href="/auth/login"
                  className="block text-sky-500 hover:text-sky-600 hover:underline"
                >
                  Back to login
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6" noValidate>
              {serverError && (
                <div className="rounded-lg bg-red-50 p-4 text-sm text-red-800" role="alert">
                  {serverError}
                </div>
              )}

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

              <Button type="submit" isLoading={isLoading} fullWidth>
                {isLoading ? 'Sending...' : 'Send reset instructions'}
              </Button>

              <p className="text-center text-sm text-gray-600">
                Remember your password?{' '}
                <Link
                  href="/auth/login"
                  className="font-medium text-sky-500 hover:text-sky-600 hover:underline"
                >
                  Sign in
                </Link>
              </p>
            </form>
          )}
        </div>

        <div className="text-center">
          <Link
            href="/"
            className="text-sm text-gray-600 hover:text-gray-900 hover:underline"
          >
            ← Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
