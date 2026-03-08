'use client';

import React, { useState } from 'react';
import type { TargetingData } from '@/lib/validations/task';

export interface TargetingOptionsProps {
  targeting: TargetingData;
  onTargetingChange: (targeting: TargetingData) => void;
  errors?: Record<string, string>;
  disabled?: boolean;
}

const GENDER_OPTIONS = [
  { value: 'all', label: 'All Genders' },
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
];

export function TargetingOptions({
  targeting,
  onTargetingChange,
  errors,
  disabled = false,
}: TargetingOptionsProps) {
  const [newInterest, setNewInterest] = useState('');
  const [newCountry, setNewCountry] = useState('');
  const [newLanguage, setNewLanguage] = useState('');

  const handleAddInterest = () => {
    if (newInterest.trim() && (!targeting.interests || targeting.interests.length < 20)) {
      onTargetingChange({
        ...targeting,
        interests: [...(targeting.interests || []), newInterest.trim()],
      });
      setNewInterest('');
    }
  };

  const handleRemoveInterest = (index: number) => {
    onTargetingChange({
      ...targeting,
      interests: targeting.interests?.filter((_, i) => i !== index),
    });
  };

  const handleAddCountry = () => {
    if (newCountry.trim() && (!targeting.countries || targeting.countries.length < 50)) {
      onTargetingChange({
        ...targeting,
        countries: [...(targeting.countries || []), newCountry.trim()],
      });
      setNewCountry('');
    }
  };

  const handleRemoveCountry = (index: number) => {
    onTargetingChange({
      ...targeting,
      countries: targeting.countries?.filter((_, i) => i !== index),
    });
  };

  const handleAddLanguage = () => {
    if (newLanguage.trim() && (!targeting.languages || targeting.languages.length < 10)) {
      onTargetingChange({
        ...targeting,
        languages: [...(targeting.languages || []), newLanguage.trim()],
      });
      setNewLanguage('');
    }
  };

  const handleRemoveLanguage = (index: number) => {
    onTargetingChange({
      ...targeting,
      languages: targeting.languages?.filter((_, i) => i !== index),
    });
  };

  return (
    <div className="w-full space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Audience Targeting
        </h3>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Define your target audience (all fields are optional)
        </p>
      </div>

      {/* Follower Range */}
      <div>
        <label className="mb-3 block text-sm font-medium text-gray-900 dark:text-gray-100">
          Follower Count Range
        </label>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="minFollowers" className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
              Minimum Followers
            </label>
            <input
              id="minFollowers"
              type="number"
              value={targeting.minFollowers || ''}
              onChange={(e) =>
                onTargetingChange({
                  ...targeting,
                  minFollowers: e.target.value ? parseInt(e.target.value, 10) : undefined,
                })
              }
              disabled={disabled}
              min={0}
              placeholder="No minimum"
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-900 transition-colors focus:border-primary-500 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:disabled:bg-gray-700"
            />
          </div>
          <div>
            <label htmlFor="maxFollowers" className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
              Maximum Followers
            </label>
            <input
              id="maxFollowers"
              type="number"
              value={targeting.maxFollowers || ''}
              onChange={(e) =>
                onTargetingChange({
                  ...targeting,
                  maxFollowers: e.target.value ? parseInt(e.target.value, 10) : undefined,
                })
              }
              disabled={disabled}
              min={0}
              placeholder="No maximum"
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-900 transition-colors focus:border-primary-500 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:disabled:bg-gray-700"
            />
          </div>
        </div>
        {errors?.followerRange && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.followerRange}</p>
        )}
      </div>

      {/* Age Range */}
      <div>
        <label className="mb-3 block text-sm font-medium text-gray-900 dark:text-gray-100">
          Age Range
        </label>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="minAge" className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
              Minimum Age
            </label>
            <input
              id="minAge"
              type="number"
              value={targeting.ageRange?.min || ''}
              onChange={(e) =>
                onTargetingChange({
                  ...targeting,
                  ageRange: {
                    min: e.target.value ? parseInt(e.target.value, 10) : 13,
                    max: targeting.ageRange?.max || 100,
                  },
                })
              }
              disabled={disabled}
              min={13}
              max={100}
              placeholder="13"
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-900 transition-colors focus:border-primary-500 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:disabled:bg-gray-700"
            />
          </div>
          <div>
            <label htmlFor="maxAge" className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
              Maximum Age
            </label>
            <input
              id="maxAge"
              type="number"
              value={targeting.ageRange?.max || ''}
              onChange={(e) =>
                onTargetingChange({
                  ...targeting,
                  ageRange: {
                    min: targeting.ageRange?.min || 13,
                    max: e.target.value ? parseInt(e.target.value, 10) : 100,
                  },
                })
              }
              disabled={disabled}
              min={13}
              max={100}
              placeholder="100"
              className="w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-900 transition-colors focus:border-primary-500 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:disabled:bg-gray-700"
            />
          </div>
        </div>
        {errors?.ageRange && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.ageRange}</p>
        )}
      </div>

      {/* Gender */}
      <div>
        <label className="mb-3 block text-sm font-medium text-gray-900 dark:text-gray-100">
          Gender
        </label>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {GENDER_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onTargetingChange({ ...targeting, gender: option.value as 'all' | 'male' | 'female' | 'other' })}
              disabled={disabled}
              className={`rounded-lg border-2 px-4 py-2 text-sm font-medium transition-all ${
                targeting.gender === option.value
                  ? 'border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300'
                  : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300'
              } ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
            >
              {option.label}
            </button>
          ))}
        </div>
        {errors?.gender && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.gender}</p>
        )}
      </div>

      {/* Interests */}
      <div>
        <label className="mb-2 block text-sm font-medium text-gray-900 dark:text-gray-100">
          Interests (max 20)
        </label>
        <div className="mb-3 flex gap-2">
          <input
            type="text"
            value={newInterest}
            onChange={(e) => setNewInterest(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddInterest()}
            disabled={disabled || (targeting.interests?.length || 0) >= 20}
            placeholder="e.g., Technology, Fashion, Sports"
            maxLength={50}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-900 transition-colors focus:border-primary-500 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:disabled:bg-gray-700"
          />
          <button
            type="button"
            onClick={handleAddInterest}
            disabled={disabled || !newInterest.trim() || (targeting.interests?.length || 0) >= 20}
            className="rounded-lg bg-primary-500 px-4 py-2 font-medium text-white transition-colors hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Add
          </button>
        </div>
        {targeting.interests && targeting.interests.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {targeting.interests.map((interest, index) => (
              <span
                key={index}
                className="inline-flex items-center gap-2 rounded-full bg-primary-100 px-3 py-1 text-sm text-primary-800 dark:bg-primary-900/30 dark:text-primary-200"
              >
                {interest}
                <button
                  type="button"
                  onClick={() => handleRemoveInterest(index)}
                  disabled={disabled}
                  className="text-primary-600 hover:text-primary-800 disabled:cursor-not-allowed disabled:opacity-50 dark:text-primary-400"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
        {errors?.interests && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.interests}</p>
        )}
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
          {targeting.interests?.length || 0} / 20 interests
        </p>
      </div>

      {/* Countries */}
      <div>
        <label className="mb-2 block text-sm font-medium text-gray-900 dark:text-gray-100">
          Countries (max 50)
        </label>
        <div className="mb-3 flex gap-2">
          <input
            type="text"
            value={newCountry}
            onChange={(e) => setNewCountry(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddCountry()}
            disabled={disabled || (targeting.countries?.length || 0) >= 50}
            placeholder="e.g., United States, Canada, UK"
            maxLength={100}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-900 transition-colors focus:border-primary-500 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:disabled:bg-gray-700"
          />
          <button
            type="button"
            onClick={handleAddCountry}
            disabled={disabled || !newCountry.trim() || (targeting.countries?.length || 0) >= 50}
            className="rounded-lg bg-primary-500 px-4 py-2 font-medium text-white transition-colors hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Add
          </button>
        </div>
        {targeting.countries && targeting.countries.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {targeting.countries.map((country, index) => (
              <span
                key={index}
                className="inline-flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-800 dark:bg-blue-900/30 dark:text-blue-200"
              >
                {country}
                <button
                  type="button"
                  onClick={() => handleRemoveCountry(index)}
                  disabled={disabled}
                  className="text-blue-600 hover:text-blue-800 disabled:cursor-not-allowed disabled:opacity-50 dark:text-blue-400"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
        {errors?.countries && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.countries}</p>
        )}
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
          {targeting.countries?.length || 0} / 50 countries
        </p>
      </div>

      {/* Languages */}
      <div>
        <label className="mb-2 block text-sm font-medium text-gray-900 dark:text-gray-100">
          Languages (max 10)
        </label>
        <div className="mb-3 flex gap-2">
          <input
            type="text"
            value={newLanguage}
            onChange={(e) => setNewLanguage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddLanguage()}
            disabled={disabled || (targeting.languages?.length || 0) >= 10}
            placeholder="e.g., English, Spanish, French"
            maxLength={50}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-900 transition-colors focus:border-primary-500 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:disabled:bg-gray-700"
          />
          <button
            type="button"
            onClick={handleAddLanguage}
            disabled={disabled || !newLanguage.trim() || (targeting.languages?.length || 0) >= 10}
            className="rounded-lg bg-primary-500 px-4 py-2 font-medium text-white transition-colors hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Add
          </button>
        </div>
        {targeting.languages && targeting.languages.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {targeting.languages.map((language, index) => (
              <span
                key={index}
                className="inline-flex items-center gap-2 rounded-full bg-green-100 px-3 py-1 text-sm text-green-800 dark:bg-green-900/30 dark:text-green-200"
              >
                {language}
                <button
                  type="button"
                  onClick={() => handleRemoveLanguage(index)}
                  disabled={disabled}
                  className="text-green-600 hover:text-green-800 disabled:cursor-not-allowed disabled:opacity-50 dark:text-green-400"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
        {errors?.languages && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.languages}</p>
        )}
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
          {targeting.languages?.length || 0} / 10 languages
        </p>
      </div>

      {/* Info Box */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          <strong>Note:</strong> All targeting options are optional. If no targeting is specified,
          your task will be available to all users. More specific targeting may result in fewer
          available task completers.
        </p>
      </div>
    </div>
  );
}
