'use client';

import React, { useState } from 'react';
import { Modal } from '../ui/modal';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

export type PaymentMethod = 'stripe' | 'paypal';

export interface DepositModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDeposit: (amount: number, paymentMethod: PaymentMethod) => Promise<void>;
  minAmount?: number;
  maxAmount?: number;
  currency?: string;
}

export function DepositModal({
  isOpen,
  onClose,
  onDeposit,
  minAmount = 10,
  maxAmount = 10000,
  currency = 'USD',
}: DepositModalProps) {
  const [amount, setAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('stripe');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (value === '' || /^\d*\.?\d{0,2}$/.test(value)) {
      setAmount(value);
      setError('');
    }
  };

  const validateAmount = (): boolean => {
    const numAmount = parseFloat(amount);

    if (!amount || isNaN(numAmount)) {
      setError('Please enter a valid amount');
      return false;
    }

    if (numAmount < minAmount) {
      setError(`Minimum deposit amount is ${formatCurrency(minAmount)}`);
      return false;
    }

    if (numAmount > maxAmount) {
      setError(`Maximum deposit amount is ${formatCurrency(maxAmount)}`);
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateAmount()) {
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      await onDeposit(parseFloat(amount), paymentMethod);
      setAmount('');
      setPaymentMethod('stripe');
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process deposit');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const handleClose = () => {
    if (!isLoading) {
      setAmount('');
      setError('');
      setPaymentMethod('stripe');
      onClose();
    }
  };

  const quickAmounts = [50, 100, 250, 500];

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Deposit Funds"
      size="md"
      closeOnOverlayClick={!isLoading}
      closeOnEscape={!isLoading}
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <Input
            label="Amount"
            type="text"
            inputMode="decimal"
            placeholder="0.00"
            value={amount}
            onChange={handleAmountChange}
            error={error}
            disabled={isLoading}
            required
            className="text-lg"
          />

          <div className="mt-3 flex flex-wrap gap-2">
            {quickAmounts.map((quickAmount) => (
              <button
                key={quickAmount}
                type="button"
                onClick={() => {
                  setAmount(quickAmount.toString());
                  setError('');
                }}
                disabled={isLoading}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                {formatCurrency(quickAmount)}
              </button>
            ))}
          </div>

          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Min: {formatCurrency(minAmount)} • Max: {formatCurrency(maxAmount)}
          </p>
        </div>

        <div>
          <label className="mb-3 block text-sm font-medium text-gray-900 dark:text-white">
            Payment Method
          </label>

          <div className="space-y-2">
            <label
              className={`flex cursor-pointer items-center gap-3 rounded-lg border p-4 transition-all ${
                paymentMethod === 'stripe'
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900'
                  : 'border-gray-300 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800'
              }`}
            >
              <input
                type="radio"
                name="paymentMethod"
                value="stripe"
                checked={paymentMethod === 'stripe'}
                onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}
                disabled={isLoading}
                className="h-4 w-4 text-primary-600"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <svg className="h-6 w-6" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M13.976 9.15c-2.172-.806-3.356-1.426-3.356-2.409 0-.831.683-1.305 1.901-1.305 2.227 0 4.515.858 6.09 1.631l.89-5.494C18.252.975 15.697 0 12.165 0 9.667 0 7.589.654 6.104 1.872 4.56 3.147 3.757 4.992 3.757 7.218c0 4.039 2.467 5.76 6.476 7.219 2.585.92 3.445 1.574 3.445 2.583 0 .98-.84 1.545-2.354 1.545-1.875 0-4.965-.921-6.99-2.109l-.9 5.555C5.175 22.99 8.385 24 11.714 24c2.641 0 4.843-.624 6.328-1.813 1.664-1.305 2.525-3.236 2.525-5.732 0-4.128-2.524-5.851-6.594-7.305h.003z" />
                  </svg>
                  <span className="font-medium text-gray-900 dark:text-white">Credit / Debit Card</span>
                </div>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Pay securely with Stripe
                </p>
              </div>
            </label>

            <label
              className={`flex cursor-pointer items-center gap-3 rounded-lg border p-4 transition-all ${
                paymentMethod === 'paypal'
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900'
                  : 'border-gray-300 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800'
              }`}
            >
              <input
                type="radio"
                name="paymentMethod"
                value="paypal"
                checked={paymentMethod === 'paypal'}
                onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}
                disabled={isLoading}
                className="h-4 w-4 text-primary-600"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <svg className="h-6 w-6" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M7.076 21.337H2.47a.641.641 0 0 1-.633-.74L4.944.901C5.026.382 5.474 0 5.998 0h7.46c2.57 0 4.578.543 5.69 1.81 1.01 1.15 1.304 2.42 1.012 4.287-.023.143-.047.288-.077.437-.983 5.05-4.349 6.797-8.647 6.797h-2.19c-.524 0-.968.382-1.05.9l-1.12 7.106zm14.146-14.42a3.35 3.35 0 0 0-.607-.541c-.013.076-.026.175-.041.254-.93 4.778-4.005 7.201-9.138 7.201h-2.19a.563.563 0 0 0-.556.479l-1.187 7.527h-.506l-.24 1.516a.56.56 0 0 0 .554.647h3.882c.46 0 .85-.334.922-.788.06-.26.76-4.852.816-5.09a.932.932 0 0 1 .923-.788h.58c3.76 0 6.705-1.528 7.565-5.946.36-1.847.174-3.388-.777-4.471z" />
                  </svg>
                  <span className="font-medium text-gray-900 dark:text-white">PayPal</span>
                </div>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Pay with your PayPal account
                </p>
              </div>
            </label>
          </div>
        </div>

        <div className="flex gap-3">
          <Button
            type="button"
            variant="ghost"
            onClick={handleClose}
            disabled={isLoading}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            isLoading={isLoading}
            disabled={isLoading}
            className="flex-1"
          >
            {isLoading ? 'Processing...' : `Deposit ${amount ? formatCurrency(parseFloat(amount)) : ''}`}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
