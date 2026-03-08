'use client';

import React, { useState } from 'react';
import type { User } from '@/lib/types/api';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ImageUpload } from '@/components/ui/image-upload';
import type { UploadedFile } from '@/components/ui/image-upload';
import {
  validateProfileForm,
  type ProfileFormData,
} from '@/lib/validations/profile';

export interface EditProfileFormProps {
  user: User;
  onSubmit: (data: ProfileFormData & { profilePictureFile?: File }) => Promise<void>;
  onCancel?: () => void;
}

export function EditProfileForm({ user, onSubmit, onCancel }: EditProfileFormProps) {
  const [formData, setFormData] = useState<ProfileFormData>({
    fullName: user.full_name || '',
    bio: user.bio || '',
    profilePicture: user.profile_picture,
  });

  const [profilePictureFile, setProfilePictureFile] = useState<File | undefined>(undefined);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [uploadError, setUploadError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Clear error for this field when user types
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const handleFilesChange = (files: UploadedFile[]) => {
    if (files.length > 0) {
      const uploadedFile = files[0];
      setProfilePictureFile(uploadedFile.file);
      setFormData((prev) => ({
        ...prev,
        profilePicture: uploadedFile.preview,
      }));
      setUploadError('');
    } else {
      setProfilePictureFile(undefined);
      setFormData((prev) => ({
        ...prev,
        profilePicture: user.profile_picture,
      }));
    }
  };

  const handleFileUploadError = (error: string) => {
    setUploadError(error);
    console.error('File upload error:', error);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate form
    const validationErrors = validateProfileForm(formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsSubmitting(true);
    setErrors({});

    try {
      await onSubmit({
        ...formData,
        profilePictureFile,
      });
    } catch (error) {
      console.error('Profile update error:', error);
      setErrors({
        submit: error instanceof Error ? error.message : 'Failed to update profile',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const formInitials = (formData.fullName || user.email || 'U').charAt(0).toUpperCase();

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Profile Picture Upload */}
      <div>
        <label className="mb-2 block text-sm font-medium text-gray-700">
          Profile Picture
        </label>
        <div className="flex items-start gap-4">
          {/* Current/Preview Picture */}
          <div className="flex-shrink-0">
            {formData.profilePicture ? (
              <img
                src={formData.profilePicture}
                alt="Profile preview"
                className="h-24 w-24 rounded-full object-cover ring-4 ring-gray-100"
              />
            ) : (
              <div className="flex h-24 w-24 items-center justify-center rounded-full bg-sky-100 text-2xl font-semibold text-sky-600 ring-4 ring-gray-100">
                {formInitials}
              </div>
            )}
          </div>

          {/* Image Upload Component */}
          <div className="flex-grow">
            <ImageUpload
              maxFiles={1}
              maxSize={5 * 1024 * 1024}
              accept="image/*"
              onFilesChange={handleFilesChange}
              onError={handleFileUploadError}
              disabled={isSubmitting}
            />
            {uploadError && (
              <p className="mt-1 text-sm text-red-600">{uploadError}</p>
            )}
          </div>
        </div>
      </div>

      {/* Full Name */}
      <Input
        label="Full Name"
        name="fullName"
        value={formData.fullName}
        onChange={handleInputChange}
        error={errors.fullName}
        required
        disabled={isSubmitting}
        placeholder="Enter your full name"
      />

      {/* Bio */}
      <div>
        <label htmlFor="bio" className="mb-2 block text-sm font-medium text-gray-700">
          Bio
        </label>
        <textarea
          id="bio"
          name="bio"
          value={formData.bio}
          onChange={handleInputChange}
          rows={4}
          disabled={isSubmitting}
          placeholder="Tell us about yourself..."
          className={`
            w-full rounded-lg border px-4 py-2.5 text-sm
            transition-colors duration-200
            focus:outline-none focus:ring-2
            disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-500
            ${
              errors.bio
                ? 'border-red-500 focus:border-red-500 focus:ring-red-200'
                : 'border-gray-300 focus:border-sky-500 focus:ring-sky-200'
            }
          `}
        />
        {errors.bio && (
          <p className="mt-1.5 text-sm text-red-600">{errors.bio}</p>
        )}
        <p className="mt-1.5 text-sm text-gray-500">
          {formData.bio?.length || 0} / 500 characters
        </p>
      </div>

      {/* Submit Error */}
      {errors.submit && (
        <div className="rounded-lg bg-red-50 p-4">
          <p className="text-sm text-red-600">{errors.submit}</p>
        </div>
      )}

      {/* Form Actions */}
      <div className="flex gap-3">
        <Button
          type="submit"
          variant="primary"
          size="md"
          isLoading={isSubmitting}
          disabled={isSubmitting}
          className="flex-1"
        >
          {isSubmitting ? 'Saving...' : 'Save Changes'}
        </Button>
        {onCancel && (
          <Button
            type="button"
            variant="outline"
            size="md"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
