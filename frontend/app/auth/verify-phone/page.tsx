'use client';

import React, { useState, FormEvent, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { validateVerificationForm, VerifyPhoneFormData } from '@/lib/validations/auth';

export default function VerifyPhonePage() {
  const router = useRouter();
  const [formData, setFormData] = useState<VerifyPhoneFormData>({
    code: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [resendTimer, setResendTimer] = useState(60);
  const [canResend, setCanResend] = useState(false);

  useEffect(() => {
    if (resendTimer > 0) {
      const timer = setTimeout(() => setResendTimer(resendTimer - 1), 1000);
      return () => clearTimeout(timer);
    } else {
      setCanResend(true);
    }
  }, [resendTimer]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    // Only allow digits and limit to 6 characters
    const sanitizedValue = value.replace(/\D/g, '').slice(0, 6);
    setFormData((prev) => ({ ...prev, [name]: sanitizedValue }));
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

  const handleResend = async () => {
    if (!canResend) return;

    setCanResend(false);
    setResendTimer(60);
    setServerError(null);

    try {
      // Simulate API call
      console.log('Resending SMS verification code...');
      await new Promise((resolve) => setTimeout(resolve, 1000));
      console.log('SMS verification code resent successfully');
    } catch (error) {
      console.error('Resend error:', error);
      setServerError(
        error instanceof Error ? error.message : 'Failed to resend verification code'
      );
      setCanResend(true);
      setResendTimer(0);
    }
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setServerError(null);

    // Validate form
    const validationErrors = validateVerificationForm(formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      // Simulate API call
      console.log('Verify phone submitted:', formData);
      await new Promise((resolve) => setTimeout(resolve, 1500));
      router.push('/dashboard');
    } catch (error) {
      console.error('Verification error:', error);
      setServerError(
        error instanceof Error
          ? error.message
          : 'Invalid verification code. Please try again.'
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
          <h2 className="mt-6 text-2xl font-bold text-gray-900">Verify your phone</h2>
          <p className="mt-2 text-sm text-gray-600">
            We&apos;ve sent a 6-digit verification code via SMS to your phone number. Please
            enter it below to verify your account.
          </p>
        </div>

        <div className="rounded-lg bg-white px-8 py-10 shadow-md">
          <form onSubmit={handleSubmit} className="space-y-6" noValidate>
            {serverError && (
              <div className="rounded-lg bg-red-50 p-4 text-sm text-red-800" role="alert">
                {serverError}
              </div>
            )}

            <Input
              type="text"
              name="code"
              label="SMS Verification Code"
              placeholder="Enter 6-digit code"
              value={formData.code}
              onChange={handleChange}
              error={errors.code}
              required
              autoComplete="one-time-code"
              disabled={isLoading}
              maxLength={6}
              inputMode="numeric"
              pattern="[0-9]*"
              className="text-center text-2xl tracking-widest"
            />

            <Button type="submit" isLoading={isLoading} fullWidth>
              {isLoading ? 'Verifying...' : 'Verify phone'}
            </Button>

            <div className="text-center">
              {canResend ? (
                <button
                  type="button"
                  onClick={handleResend}
                  className="text-sm text-sky-500 hover:text-sky-600 hover:underline"
                >
                  Resend verification code
                </button>
              ) : (
                <p className="text-sm text-gray-600">
                  Resend code in{' '}
                  <span className="font-semibold text-gray-900">{resendTimer}s</span>
                </p>
              )}
            </div>
          </form>
        </div>

        <div className="text-center space-y-2">
          <p className="text-sm text-gray-600">
            Need help?{' '}
            <Link
              href="/support"
              className="text-sky-500 hover:text-sky-600 hover:underline"
            >
              Contact support
            </Link>
          </p>
          <Link
            href="/auth/login"
            className="block text-sm text-gray-600 hover:text-gray-900 hover:underline"
          >
            ← Back to login
          </Link>
        </div>
      </div>
    </div>
  );
}
