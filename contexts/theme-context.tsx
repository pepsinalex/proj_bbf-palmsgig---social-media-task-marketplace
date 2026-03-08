'use client';

import React, { createContext, useCallback, useEffect, useState } from 'react';

// Theme type
export type Theme = 'light' | 'dark' | 'system';

// Theme context value interface
interface ThemeContextValue {
  theme: Theme;
  effectiveTheme: 'light' | 'dark';
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

// Create the context with undefined as initial value
const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

// ThemeProvider props
interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
}

// Default storage key
const DEFAULT_STORAGE_KEY = 'palmsgig_theme';

// Helper function to get system theme preference
const getSystemTheme = (): 'light' | 'dark' => {
  if (typeof window === 'undefined') return 'light';

  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }

  return 'light';
};

// Helper function to safely store theme preference
const storeTheme = (theme: Theme, storageKey: string): void => {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(storageKey, theme);
  } catch (error) {
    console.error('Error storing theme preference:', error);
  }
};

// Helper function to safely retrieve theme preference
const retrieveTheme = (storageKey: string, defaultTheme: Theme): Theme => {
  if (typeof window === 'undefined') return defaultTheme;
  try {
    const stored = localStorage.getItem(storageKey);
    if (stored && (stored === 'light' || stored === 'dark' || stored === 'system')) {
      return stored as Theme;
    }
  } catch (error) {
    console.error('Error retrieving theme preference:', error);
  }
  return defaultTheme;
};

// Helper function to apply theme to document
const applyTheme = (effectiveTheme: 'light' | 'dark'): void => {
  if (typeof window === 'undefined') return;

  const root = document.documentElement;

  if (effectiveTheme === 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }

  // Update meta theme-color for mobile browsers
  const metaThemeColor = document.querySelector('meta[name="theme-color"]');
  if (metaThemeColor) {
    metaThemeColor.setAttribute('content', effectiveTheme === 'dark' ? '#1f2937' : '#0ea5e9');
  }
};

// ThemeProvider component
export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = DEFAULT_STORAGE_KEY,
}: ThemeProviderProps) {
  // Initialize theme from storage or default
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window === 'undefined') return defaultTheme;
    return retrieveTheme(storageKey, defaultTheme);
  });

  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>(() => getSystemTheme());

  // Calculate effective theme
  const effectiveTheme: 'light' | 'dark' = theme === 'system' ? systemTheme : theme;

  // Set theme function
  const setTheme = useCallback(
    (newTheme: Theme) => {
      setThemeState(newTheme);
      storeTheme(newTheme, storageKey);
    },
    [storageKey]
  );

  // Toggle theme function (cycles through light -> dark -> light)
  const toggleTheme = useCallback(() => {
    setTheme(effectiveTheme === 'light' ? 'dark' : 'light');
  }, [effectiveTheme, setTheme]);

  // Apply theme to document when effective theme changes
  useEffect(() => {
    applyTheme(effectiveTheme);
  }, [effectiveTheme]);

  // Listen for system theme changes
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent) => {
      setSystemTheme(e.matches ? 'dark' : 'light');
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }

    // Fallback for older browsers
    if (mediaQuery.addListener) {
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, []);

  // Prevent flash of unstyled content on initial load
  useEffect(() => {
    // Apply theme immediately on mount
    applyTheme(effectiveTheme);
  }, []);

  // Context value
  const value: ThemeContextValue = {
    theme,
    effectiveTheme,
    setTheme,
    toggleTheme,
  };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

// Export the context for use in custom hook
export { ThemeContext };
