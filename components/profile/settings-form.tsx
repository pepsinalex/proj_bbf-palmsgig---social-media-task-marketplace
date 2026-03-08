'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import type { SettingsFormData } from '@/lib/validations/profile';

export interface SettingsFormProps {
  initialSettings: SettingsFormData;
  onSubmit: (data: SettingsFormData) => Promise<void>;
}

export function SettingsForm({ initialSettings, onSubmit }: SettingsFormProps) {
  const [formData, setFormData] = useState<SettingsFormData>(initialSettings);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');

  const handleToggle = (field: keyof SettingsFormData) => {
    setFormData((prev) => ({
      ...prev,
      [field]: !prev[field],
    }));
    setError('');
    setSuccessMessage('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    setSuccessMessage('');

    try {
      await onSubmit(formData);
      setSuccessMessage('Settings saved successfully');
    } catch (err) {
      console.error('Settings update error:', err);
      setError(err instanceof Error ? err.message : 'Failed to update settings');
    } finally {
      setIsSubmitting(false);
    }
  };

  const settingsGroups = [
    {
      title: 'Notifications',
      description: 'Manage how you receive notifications',
      settings: [
        {
          key: 'emailNotifications' as keyof SettingsFormData,
          label: 'Email Notifications',
          description: 'Receive notifications via email',
        },
        {
          key: 'taskNotifications' as keyof SettingsFormData,
          label: 'Task Updates',
          description: 'Get notified about task updates and completions',
        },
        {
          key: 'marketingEmails' as keyof SettingsFormData,
          label: 'Marketing Emails',
          description: 'Receive marketing emails and promotional offers',
        },
      ],
    },
    {
      title: 'Security',
      description: 'Manage your account security settings',
      settings: [
        {
          key: 'twoFactorEnabled' as keyof SettingsFormData,
          label: 'Two-Factor Authentication',
          description: 'Add an extra layer of security to your account',
        },
      ],
    },
  ];

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Settings Groups */}
      {settingsGroups.map((group, groupIndex) => (
        <div key={groupIndex} className="space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{group.title}</h3>
            <p className="mt-1 text-sm text-gray-500">{group.description}</p>
          </div>

          <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-6">
            {group.settings.map((setting, settingIndex) => (
              <div
                key={settingIndex}
                className="flex items-center justify-between border-b border-gray-100 pb-4 last:border-b-0 last:pb-0"
              >
                <div className="flex-grow">
                  <label
                    htmlFor={setting.key}
                    className="block text-sm font-medium text-gray-900"
                  >
                    {setting.label}
                  </label>
                  <p className="mt-0.5 text-sm text-gray-500">{setting.description}</p>
                </div>

                {/* Toggle Switch */}
                <button
                  type="button"
                  id={setting.key}
                  role="switch"
                  aria-checked={formData[setting.key]}
                  onClick={() => handleToggle(setting.key)}
                  disabled={isSubmitting}
                  className={`
                    relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent
                    transition-colors duration-200 ease-in-out
                    focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2
                    disabled:cursor-not-allowed disabled:opacity-50
                    ${formData[setting.key] ? 'bg-sky-600' : 'bg-gray-200'}
                  `}
                >
                  <span className="sr-only">{setting.label}</span>
                  <span
                    aria-hidden="true"
                    className={`
                      pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0
                      transition duration-200 ease-in-out
                      ${formData[setting.key] ? 'translate-x-5' : 'translate-x-0'}
                    `}
                  />
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Success Message */}
      {successMessage && (
        <div className="rounded-lg bg-green-50 p-4">
          <div className="flex items-center gap-2">
            <svg
              className="h-5 w-5 text-green-600"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm font-medium text-green-800">{successMessage}</p>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="rounded-lg bg-red-50 p-4">
          <div className="flex items-center gap-2">
            <svg
              className="h-5 w-5 text-red-600"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm font-medium text-red-800">{error}</p>
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="flex justify-end">
        <Button
          type="submit"
          variant="primary"
          size="md"
          isLoading={isSubmitting}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Saving...' : 'Save Settings'}
        </Button>
      </div>
    </form>
  );
}
