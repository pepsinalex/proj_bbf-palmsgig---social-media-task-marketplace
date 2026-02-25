import Image from 'next/image';
import { BRAND_ASSETS } from '@/lib/constants/brand';

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b bg-white">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="relative h-8 w-32">
            <Image
              src={BRAND_ASSETS.logos.horizontal.ORANGE}
              alt="PalmsGig"
              fill
              className="object-contain"
              priority
            />
          </div>
          <nav className="flex gap-6">
            <a href="#features" className="text-gray-600 hover:text-gray-900">
              Features
            </a>
            <a href="#how-it-works" className="text-gray-600 hover:text-gray-900">
              How It Works
            </a>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <section className="bg-gradient-to-br from-primary-50 to-primary-100 py-20">
          <div className="container mx-auto px-4 text-center">
            <h1 className="mb-6 text-5xl font-bold text-gray-900">
              Welcome to PalmsGig
            </h1>
            <p className="mb-8 text-xl text-gray-700">
              The social media task marketplace connecting creators and brands
            </p>
            <div className="flex justify-center gap-4">
              <button className="rounded-lg bg-primary-600 px-8 py-3 font-semibold text-white hover:bg-primary-700">
                Get Started
              </button>
              <button className="rounded-lg border border-primary-600 px-8 py-3 font-semibold text-primary-600 hover:bg-primary-50">
                Learn More
              </button>
            </div>
          </div>
        </section>

        <section id="features" className="py-20">
          <div className="container mx-auto px-4">
            <h2 className="mb-12 text-center text-4xl font-bold text-gray-900">
              Key Features
            </h2>
            <div className="grid gap-8 md:grid-cols-3">
              <div className="rounded-lg bg-white p-6 shadow-md">
                <h3 className="mb-4 text-2xl font-semibold text-gray-900">
                  Task Discovery
                </h3>
                <p className="text-gray-600">
                  Find and complete social media tasks that match your interests and audience.
                </p>
              </div>
              <div className="rounded-lg bg-white p-6 shadow-md">
                <h3 className="mb-4 text-2xl font-semibold text-gray-900">
                  Secure Payments
                </h3>
                <p className="text-gray-600">
                  Get paid securely through our integrated payment system with escrow protection.
                </p>
              </div>
              <div className="rounded-lg bg-white p-6 shadow-md">
                <h3 className="mb-4 text-2xl font-semibold text-gray-900">
                  Easy Management
                </h3>
                <p className="text-gray-600">
                  Manage your tasks, earnings, and profile all in one convenient dashboard.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="bg-gray-100 py-20">
          <div className="container mx-auto px-4">
            <h2 className="mb-12 text-center text-4xl font-bold text-gray-900">
              How It Works
            </h2>
            <div className="grid gap-8 md:grid-cols-3">
              <div className="text-center">
                <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-primary-600 text-2xl font-bold text-white">
                  1
                </div>
                <h3 className="mb-2 text-xl font-semibold text-gray-900">
                  Create Account
                </h3>
                <p className="text-gray-600">
                  Sign up and connect your social media accounts
                </p>
              </div>
              <div className="text-center">
                <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-primary-600 text-2xl font-bold text-white">
                  2
                </div>
                <h3 className="mb-2 text-xl font-semibold text-gray-900">
                  Browse Tasks
                </h3>
                <p className="text-gray-600">
                  Discover tasks that match your profile and interests
                </p>
              </div>
              <div className="text-center">
                <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-primary-600 text-2xl font-bold text-white">
                  3
                </div>
                <h3 className="mb-2 text-xl font-semibold text-gray-900">
                  Earn Rewards
                </h3>
                <p className="text-gray-600">
                  Complete tasks and get paid securely
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t bg-white py-8">
        <div className="container mx-auto px-4 text-center">
          <div className="mb-4 flex justify-center">
            <div className="relative h-8 w-32">
              <Image
                src={BRAND_ASSETS.logos.horizontal.ORANGE}
                alt="PalmsGig"
                fill
                className="object-contain"
              />
            </div>
          </div>
          <p className="text-gray-600">&copy; 2024 PalmsGig. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
