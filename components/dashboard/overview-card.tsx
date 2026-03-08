import React from 'react';
import { Card, CardContent } from '../ui/card';
import { Skeleton } from '../ui/skeleton';

export interface OverviewCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  loading?: boolean;
}

export function OverviewCard({ title, value, icon, trend, loading = false }: OverviewCardProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <Skeleton width="60%" height="0.875rem" />
              <Skeleton width="80%" height="1.875rem" className="mt-2" />
            </div>
            <Skeleton circle width="3rem" height="3rem" />
          </div>
          {trend && <Skeleton width="40%" height="0.75rem" className="mt-4" />}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
            <h3 className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">{value}</h3>
            {trend && (
              <div className="mt-4 flex items-center gap-1">
                {trend.isPositive ? (
                  <svg className="h-4 w-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                  </svg>
                ) : (
                  <svg className="h-4 w-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                  </svg>
                )}
                <span
                  className={`text-xs font-medium ${
                    trend.isPositive ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {Math.abs(trend.value)}%
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">vs last month</span>
              </div>
            )}
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400">
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
