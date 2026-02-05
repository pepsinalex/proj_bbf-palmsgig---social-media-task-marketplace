'use client';

import React, { useState } from 'react';
import { Modal } from '../ui/modal';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

export type PayoutMethod = 'bank_account' | 'paypal';

export interface WithdrawalModalProps {
  isOpen: boolean;
  onClose: () => void;
  onWithdraw: (amount: number, payoutMethod: PayoutMethod) => Promise<void>;
  availableBalance: number;
  minAmount?: number;
  currency?: string;
}

export function WithdrawalModal({
  isOpen,
  onClose,
  onWithdraw,
  availableBalance,
  minAmount = 10,
  currency = 'USD',
}: WithdrawalModalProps) {
  const [amount, setAmount] = useState('');
  const [payoutMethod, setPayoutMethod] = useState<PayoutMethod>('bank_account');
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
      setError(`Minimum withdrawal amount is ${formatCurrency(minAmount)}`);
      return false;
    }

    if (numAmount > availableBalance) {
      setError(`Amount exceeds available balance of ${formatCurrency(availableBalance)}`);
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
      await onWithdraw(parseFloat(amount), payoutMethod);
      setAmount('');
      setPayoutMethod('bank_account');
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process withdrawal');
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
      setPayoutMethod('bank_account');
      onClose();
    }
  };

  const handleMaxClick = () => {
    setAmount(availableBalance.toFixed(2));
    setError('');
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Withdraw Funds"
      size="md"
      closeOnOverlayClick={!isLoading}
      closeOnEscape={!isLoading}
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="rounded-lg bg-blue-50 p-4 dark:bg-blue-900">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700 dark:text-gray-300">Available Balance</span>
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              {formatCurrency(availableBalance)}
            </span>
          </div>
        </div>

        <div>
          <div className="flex items-end gap-2">
            <div className="flex-1">
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
            </div>
            <Button
              type="button"
              variant="outline"
              size="md"
              onClick={handleMaxClick}
              disabled={isLoading || availableBalance === 0}
              className="mb-6"
            >
              Max
            </Button>
          </div>

          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Min: {formatCurrency(minAmount)}
          </p>
        </div>

        <div>
          <label className="mb-3 block text-sm font-medium text-gray-900 dark:text-white">
            Payout Method
          </label>

          <div className="space-y-2">
            <label
              className={`flex cursor-pointer items-center gap-3 rounded-lg border p-4 transition-all ${
                payoutMethod === 'bank_account'
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900'
                  : 'border-gray-300 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800'
              }`}
            >
              <input
                type="radio"
                name="payoutMethod"
                value="bank_account"
                checked={payoutMethod === 'bank_account'}
                onChange={(e) => setPayoutMethod(e.target.value as PayoutMethod)}
                disabled={isLoading}
                className="h-4 w-4 text-primary-600"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <svg
                    className="h-6 w-6 text-gray-600 dark:text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
                    />
                  </svg>
                  <span className="font-medium text-gray-900 dark:text-white">Bank Account</span>
                </div>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Direct transfer to your bank account
                </p>
              </div>
            </label>

            <label
              className={`flex cursor-pointer items-center gap-3 rounded-lg border p-4 transition-all ${
                payoutMethod === 'paypal'
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900'
                  : 'border-gray-300 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800'
              }`}
            >
              <input
                type="radio"
                name="payoutMethod"
                value="paypal"
                checked={payoutMethod === 'paypal'}
                onChange={(e) => setPayoutMethod(e.target.value as PayoutMethod)}
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
                  Withdraw to your PayPal account
                </p>
              </div>
            </label>
          </div>
        </div>

        <div className="rounded-lg bg-yellow-50 p-4 dark:bg-yellow-900">
          <p className="text-xs text-yellow-800 dark:text-yellow-200">
            Processing time: 2-5 business days. You'll receive a confirmation email once your
            withdrawal is processed.
          </p>
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
            disabled={isLoading || availableBalance === 0}
            className="flex-1"
          >
            {isLoading
              ? 'Processing...'
              : `Withdraw ${amount ? formatCurrency(parseFloat(amount)) : ''}`}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
