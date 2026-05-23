import React from 'react';

export type CardVariant = 'default' | 'elevated' | 'outlined' | 'interactive';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: CardVariant;
}

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const variantStyles: Record<CardVariant, string> = {
  default:
    'border border-gray-200 bg-white shadow-card dark:border-gray-700 dark:bg-gray-800',
  elevated:
    'border border-transparent bg-white shadow-elevated dark:bg-gray-800',
  outlined:
    'border border-gray-200 bg-transparent dark:border-gray-700',
  interactive:
    'border border-gray-200 bg-white shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-primary-200 hover:shadow-brand-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-primary-700',
};

export function Card({
  children,
  className = '',
  variant = 'default',
  ...props
}: CardProps) {
  return (
    <div
      className={`rounded-lg ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '', ...props }: CardHeaderProps) {
  return (
    <div
      className={`border-b border-gray-200 px-6 py-4 dark:border-gray-700 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardContent({ children, className = '', ...props }: CardContentProps) {
  return (
    <div className={`px-6 py-4 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ children, className = '', ...props }: CardFooterProps) {
  return (
    <div
      className={`border-t border-gray-200 px-6 py-4 dark:border-gray-700 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode;
}

export function CardTitle({ children, className = '', ...props }: CardTitleProps) {
  return (
    <h3
      className={`text-lg font-semibold tracking-tight text-secondary-900 dark:text-gray-50 ${className}`}
      {...props}
    >
      {children}
    </h3>
  );
}

export interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode;
}

export function CardDescription({ children, className = '', ...props }: CardDescriptionProps) {
  return (
    <p
      className={`mt-1 text-sm text-gray-500 dark:text-gray-400 ${className}`}
      {...props}
    >
      {children}
    </p>
  );
}
