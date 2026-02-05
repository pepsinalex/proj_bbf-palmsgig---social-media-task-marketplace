'use client';

import React from 'react';
import { AuthProvider } from '../contexts/auth-context';
import { ThemeProvider } from '../contexts/theme-context';

interface ProvidersProps {
  children: React.ReactNode;
}

/**
 * Providers component that wraps the application with all context providers
 *
 * This component is marked as 'use client' to enable client-side context providers
 * while keeping the root layout as a server component for metadata support.
 */
export function Providers({ children }: ProvidersProps) {
  return (
    <ThemeProvider defaultTheme="system" storageKey="palmsgig_theme">
      <AuthProvider>{children}</AuthProvider>
    </ThemeProvider>
  );
}
