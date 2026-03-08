import { useContext } from 'react';
import { AuthContext } from '../contexts/auth-context';

/**
 * Custom hook for accessing authentication context
 *
 * This hook provides access to the authentication state and methods.
 * It must be used within an AuthProvider.
 *
 * @throws {Error} If used outside of AuthProvider
 * @returns {AuthContextValue} Authentication context value
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { user, isAuthenticated, login, logout } = useAuth();
 *
 *   if (!isAuthenticated) {
 *     return <LoginForm onSubmit={login} />;
 *   }
 *
 *   return (
 *     <div>
 *       <h1>Welcome, {user.fullName}</h1>
 *       <button onClick={logout}>Logout</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useAuth() {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error(
      'useAuth must be used within an AuthProvider. ' +
        'Make sure your component is wrapped with <AuthProvider>.'
    );
  }

  return context;
}
