import { Metadata } from 'next';
import Link from 'next/link';
import { LoginForm } from '@/components/auth/login-form';

export const metadata: Metadata = {
  title: 'Login - PalmsGig',
  description: 'Sign in to your PalmsGig account',
};

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <Link href="/" className="inline-block">
            <h1 className="text-3xl font-bold text-[#FF8F33]">PalmsGig</h1>
          </Link>
          <h2 className="mt-6 text-2xl font-bold text-[#001046]">
            Welcome back
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Sign in to continue to your account
          </p>
        </div>

        <div className="rounded-lg bg-white px-8 py-10 shadow-md">
          <LoginForm />
        </div>

        <div className="text-center">
          <Link
            href="/"
            className="text-sm text-gray-600 hover:text-[#FF8F33] hover:underline"
          >
            ← Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
