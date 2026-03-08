'use client';

import React from 'react';
import { Card, CardContent } from '../ui/card';

export interface CreatorProfileProps {
  name: string;
  avatar?: string;
  rating: number;
  totalReviews: number;
  tasksCompleted: number;
  successRate: number;
  verified?: boolean;
  joinedDate?: string;
  className?: string;
}

export function CreatorProfile({
  name,
  avatar,
  rating,
  totalReviews,
  tasksCompleted,
  successRate,
  verified = false,
  joinedDate,
  className = '',
}: CreatorProfileProps) {
  const renderStars = (rating: number) => {
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;

    for (let i = 0; i < 5; i++) {
      if (i < fullStars) {
        stars.push(
          <svg
            key={i}
            className="h-5 w-5 text-yellow-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        );
      } else if (i === fullStars && hasHalfStar) {
        stars.push(
          <svg
            key={i}
            className="h-5 w-5 text-yellow-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <defs>
              <linearGradient id="half">
                <stop offset="50%" stopColor="currentColor" />
                <stop offset="50%" stopColor="#D1D5DB" stopOpacity="1" />
              </linearGradient>
            </defs>
            <path
              fill="url(#half)"
              d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
            />
          </svg>
        );
      } else {
        stars.push(
          <svg
            key={i}
            className="h-5 w-5 text-gray-300 dark:text-gray-600"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        );
      }
    }
    return stars;
  };

  return (
    <Card className={className}>
      <CardContent>
        <div className="flex items-start gap-4">
          <div className="relative">
            <div className="h-16 w-16 overflow-hidden rounded-full bg-gradient-to-br from-sky-400 to-blue-600">
              {avatar ? (
                <img src={avatar} alt={name} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-2xl font-bold text-white">
                  {name.charAt(0).toUpperCase()}
                </div>
              )}
            </div>
            {verified && (
              <div className="absolute -bottom-1 -right-1 rounded-full bg-white p-0.5 dark:bg-gray-800">
                <svg
                  className="h-5 w-5 text-blue-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
            )}
          </div>

          <div className="flex-1">
            <div className="mb-2 flex items-center gap-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{name}</h3>
              {verified && (
                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                  Verified
                </span>
              )}
            </div>

            <div className="mb-3 flex items-center gap-2">
              <div className="flex items-center">{renderStars(rating)}</div>
              <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {rating.toFixed(1)}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                ({totalReviews} {totalReviews === 1 ? 'review' : 'reviews'})
              </span>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Tasks Completed</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {tasksCompleted}
                </p>
              </div>

              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Success Rate</p>
                <p className="text-lg font-semibold text-green-600 dark:text-green-400">
                  {successRate}%
                </p>
              </div>

              {joinedDate && (
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Member Since</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {new Date(joinedDate).toLocaleDateString('en-US', {
                      month: 'short',
                      year: 'numeric',
                    })}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
