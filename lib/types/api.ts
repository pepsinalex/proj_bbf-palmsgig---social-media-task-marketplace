// API Types for PalmsGig Platform

// User types
export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'client' | 'influencer' | 'admin';
  email_verified: boolean;
  phone_verified: boolean;
  profile_picture?: string;
  bio?: string;
  phone_number?: string;
  socialAccounts?: SocialAccount[];
  wallet_balance?: number;
  created_at: string;
  updated_at: string;
}

export interface SocialAccount {
  id: string;
  platform: 'instagram' | 'twitter' | 'facebook' | 'tiktok' | 'youtube';
  username: string;
  followers: number;
  verified: boolean;
  connectedAt: string;
}

// Authentication types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  fullName: string;
  role: 'client' | 'influencer';
  termsAccepted: boolean;
}

export interface AuthResponse {
  user: User;
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

export interface VerifyEmailRequest {
  email: string;
  code: string;
}

export interface VerifyPhoneRequest {
  phone: string;
  code: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  password: string;
}

// Task types
export interface Task {
  id: string;
  title: string;
  description: string;
  platform: 'instagram' | 'twitter' | 'facebook' | 'tiktok' | 'youtube';
  taskType:
    | 'post'
    | 'story'
    | 'reels'
    | 'like'
    | 'comment'
    | 'follow'
    | 'share'
    | 'video';
  status: 'draft' | 'active' | 'paused' | 'completed' | 'cancelled';
  budget: number;
  rewardPerAction: number;
  totalSlots: number;
  filledSlots: number;
  requirements: TaskRequirement[];
  instructions: string;
  proofRequired: boolean;
  clientId: string;
  client?: User;
  startDate?: string;
  endDate?: string;
  createdAt: string;
  updatedAt: string;
}

export interface TaskRequirement {
  type: 'followers' | 'engagement_rate' | 'account_age' | 'verified';
  value: string | number | boolean;
  operator?: 'gte' | 'lte' | 'eq';
}

export interface CreateTaskRequest {
  title: string;
  description: string;
  platform: Task['platform'];
  taskType: Task['taskType'];
  budget: number;
  rewardPerAction: number;
  totalSlots: number;
  requirements: TaskRequirement[];
  instructions: string;
  proofRequired: boolean;
  startDate?: string;
  endDate?: string;
}

export interface UpdateTaskRequest extends Partial<CreateTaskRequest> {
  status?: Task['status'];
}

export interface TaskSubmission {
  id: string;
  taskId: string;
  task?: Task;
  influencerId: string;
  influencer?: User;
  status: 'pending' | 'approved' | 'rejected';
  proofUrl?: string;
  proofDescription?: string;
  rejectionReason?: string;
  rewardAmount: number;
  submittedAt: string;
  reviewedAt?: string;
}

export interface SubmitTaskProofRequest {
  taskId: string;
  proofUrl?: string;
  proofDescription?: string;
}

export interface ReviewSubmissionRequest {
  submissionId: string;
  status: 'approved' | 'rejected';
  rejectionReason?: string;
}

// Wallet and transaction types
export interface Wallet {
  id: string;
  userId: string;
  balance: number;
  currency: string;
  createdAt: string;
  updatedAt: string;
}

export interface Transaction {
  id: string;
  walletId: string;
  type: 'deposit' | 'withdrawal' | 'payment' | 'refund' | 'reward';
  amount: number;
  currency: string;
  status: 'pending' | 'completed' | 'failed' | 'cancelled';
  description: string;
  reference?: string;
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface DepositRequest {
  amount: number;
  paymentMethod: 'stripe' | 'paypal';
  returnUrl?: string;
}

export interface WithdrawRequest {
  amount: number;
  withdrawalMethod: 'bank_transfer' | 'paypal';
  bankAccount?: BankAccount;
  paypalEmail?: string;
}

export interface BankAccount {
  accountNumber: string;
  routingNumber: string;
  accountHolderName: string;
  bankName: string;
}

// Dashboard types
export interface DashboardStats {
  totalTasks: number;
  activeTasks: number;
  completedTasks: number;
  totalEarnings: number;
  pendingSubmissions: number;
  walletBalance: number;
  recentTransactions: Transaction[];
  recentTasks: Task[];
}

// API response wrapper types
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  timestamp: string;
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  timestamp: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
  timestamp: string;
}

// Query parameters types
export interface PaginationParams {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface TaskFilters extends PaginationParams {
  status?: Task['status'];
  platform?: Task['platform'];
  taskType?: Task['taskType'];
  minBudget?: number;
  maxBudget?: number;
  clientId?: string;
}

export interface TransactionFilters extends PaginationParams {
  type?: Transaction['type'];
  status?: Transaction['status'];
  startDate?: string;
  endDate?: string;
  minAmount?: number;
  maxAmount?: number;
}
