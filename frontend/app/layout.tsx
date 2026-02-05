import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'PalmsGig - Social Media Task Marketplace',
  description:
    'Connect with social media influencers and complete tasks to earn rewards on PalmsGig.',
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#0ea5e9',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 antialiased">{children}</body>
    </html>
  );
}
