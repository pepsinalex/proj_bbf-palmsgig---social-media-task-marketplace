import { Metadata } from 'next';
import Link from 'next/link';
import { RegisterForm } from '@/components/auth/register-form';
import { Logo } from '@/components/ui/logo';

export const metadata: Metadata = {
  title: 'Register - PalmsGig',
  description: 'Create your PalmsGig account',
};

export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <Link href="/" className="inline-block" aria-label="PalmsGig home">
            <Logo
              variant="horizontal"
              theme="orange"
              width={180}
              height={48}
              priority
              className="mx-auto"
            />
          </Link>
          <h2 className="mt-6 text-2xl font-bold text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Join PalmsGig and start earning rewards
          </p>
        </div>

        <div className="rounded-lg bg-white px-8 py-10 shadow-md">
          <RegisterForm />
        </div>

        <div className="text-center">
          <Link
            href="/"
            className="text-sm text-gray-600 hover:text-gray-900 hover:underline"
          >
            ← Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
