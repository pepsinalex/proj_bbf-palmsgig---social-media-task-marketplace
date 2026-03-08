import React from 'react';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  width?: string | number;
  height?: string | number;
  circle?: boolean;
  count?: number;
}

export function Skeleton({
  width,
  height = '1rem',
  circle = false,
  count = 1,
  className = '',
  ...props
}: SkeletonProps) {
  const skeletonStyle: React.CSSProperties = {
    width: width || '100%',
    height,
  };

  const baseClasses = circle
    ? 'rounded-full'
    : 'rounded';

  const animationClasses = 'animate-pulse bg-gray-200 dark:bg-gray-700';

  const fullClassName = `${baseClasses} ${animationClasses} ${className}`;

  if (count === 1) {
    return <div className={fullClassName} style={skeletonStyle} aria-busy="true" aria-live="polite" {...props} />;
  }

  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className={`${fullClassName} ${index > 0 ? 'mt-2' : ''}`}
          style={skeletonStyle}
          aria-busy="true"
          aria-live="polite"
          {...props}
        />
      ))}
    </>
  );
}
