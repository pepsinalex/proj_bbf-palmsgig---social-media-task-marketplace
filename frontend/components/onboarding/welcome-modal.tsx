'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Modal } from '@/components/ui/modal';
import { Button } from '@/components/ui/button';
import { UserRole } from '@/lib/types/api';

export type OnboardingRole = UserRole.EMPLOYER | UserRole.EMPLOYEE;

export interface WelcomeModalProps {
  isOpen: boolean;
  role: OnboardingRole;
  userName?: string;
  onClose: () => void;
  onComplete?: (action: 'started' | 'skipped') => void | Promise<void>;
}

interface OnboardingContent {
  title: string;
  greeting: string;
  description: string;
  steps: Array<{ title: string; description: string }>;
  primaryCtaLabel: string;
  primaryCtaHref: string;
}

const ONBOARDING_CONTENT: Record<OnboardingRole, OnboardingContent> = {
  [UserRole.EMPLOYER]: {
    title: 'Welcome to PalmsGig',
    greeting: 'Ready to get tasks done?',
    description:
      'As an Employer, you can post tasks, set your budget, and hire skilled workers to grow your social media presence.',
    steps: [
      {
        title: 'Create your first task',
        description:
          'Define the work you need done — choose a platform, write clear instructions, and add proof requirements.',
      },
      {
        title: 'Set your budget',
        description:
          'Fund your task with a budget you control. Pay per action, track spending, and top up your wallet whenever you need.',
      },
      {
        title: 'Hire and review workers',
        description:
          'Review submissions, approve quality work, and release payments. Build a roster of trusted workers over time.',
      },
    ],
    primaryCtaLabel: 'Create your first task',
    primaryCtaHref: '/dashboard/tasks/create',
  },
  [UserRole.EMPLOYEE]: {
    title: 'Welcome to PalmsGig',
    greeting: 'Ready to start earning?',
    description:
      'As an Employee, you can browse available jobs, complete tasks on social platforms you already use, and earn rewards.',
    steps: [
      {
        title: 'Browse available jobs',
        description:
          'Explore tasks across Instagram, Twitter, TikTok and more. Filter by reward, platform, or task type.',
      },
      {
        title: 'Complete tasks and submit proof',
        description:
          'Follow each task’s instructions, then submit your proof of completion — screenshots, links, or descriptions.',
      },
      {
        title: 'Earn and withdraw',
        description:
          'Once your submission is approved, your reward is credited to your wallet. Withdraw whenever you’re ready.',
      },
    ],
    primaryCtaLabel: 'Browse available jobs',
    primaryCtaHref: '/dashboard/tasks',
  },
};

export function WelcomeModal({
  isOpen,
  role,
  userName,
  onClose,
  onComplete,
}: WelcomeModalProps) {
  const router = useRouter();
  const [isProcessing, setIsProcessing] = React.useState(false);

  const content = ONBOARDING_CONTENT[role];

  const finalize = async (action: 'started' | 'skipped') => {
    if (isProcessing) return;
    setIsProcessing(true);
    try {
      if (onComplete) {
        await onComplete(action);
      }
    } catch (error) {
      console.error('Failed to record onboarding completion:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleGetStarted = async () => {
    await finalize('started');
    onClose();
    router.push(content.primaryCtaHref);
  };

  const handleSkip = async () => {
    await finalize('skipped');
    onClose();
  };

  const greeting = userName
    ? `${content.greeting.replace('Ready', `Welcome, ${userName.split(' ')[0]} — ready`)}`
    : content.greeting;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleSkip}
      title={content.title}
      size="lg"
      closeOnOverlayClick={false}
      closeOnEscape={false}
      showCloseButton={false}
      footer={
        <>
          <Button
            type="button"
            variant="ghost"
            onClick={handleSkip}
            disabled={isProcessing}
          >
            Skip for now
          </Button>
          <Button
            type="button"
            variant="primary"
            onClick={handleGetStarted}
            isLoading={isProcessing}
          >
            {content.primaryCtaLabel}
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        <div>
          <p className="text-lg font-semibold text-[#001046]">{greeting}</p>
          <p className="mt-2 text-sm text-gray-600">{content.description}</p>
        </div>

        <ol className="space-y-3" aria-label="Onboarding steps">
          {content.steps.map((step, index) => (
            <li
              key={step.title}
              className="flex gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3"
            >
              <span
                className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-[#FF8F33] text-sm font-semibold text-white"
                aria-hidden="true"
              >
                {index + 1}
              </span>
              <div>
                <p className="text-sm font-semibold text-[#001046]">
                  {step.title}
                </p>
                <p className="mt-0.5 text-sm text-gray-600">
                  {step.description}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </Modal>
  );
}

export default WelcomeModal;
