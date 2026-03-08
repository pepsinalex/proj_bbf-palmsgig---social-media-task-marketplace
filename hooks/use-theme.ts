import { useContext } from 'react';
import { ThemeContext } from '../contexts/theme-context';

/**
 * Custom hook for accessing theme context
 *
 * This hook provides access to the current theme and methods to change it.
 * It must be used within a ThemeProvider.
 *
 * @throws {Error} If used outside of ThemeProvider
 * @returns {ThemeContextValue} Theme context value
 *
 * @example
 * ```tsx
 * function ThemeToggle() {
 *   const { theme, effectiveTheme, setTheme, toggleTheme } = useTheme();
 *
 *   return (
 *     <div>
 *       <p>Current theme: {theme}</p>
 *       <p>Effective theme: {effectiveTheme}</p>
 *       <button onClick={toggleTheme}>Toggle Theme</button>
 *       <button onClick={() => setTheme('system')}>Use System Theme</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useTheme() {
  const context = useContext(ThemeContext);

  if (context === undefined) {
    throw new Error(
      'useTheme must be used within a ThemeProvider. ' +
        'Make sure your component is wrapped with <ThemeProvider>.'
    );
  }

  return context;
}
