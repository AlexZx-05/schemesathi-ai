import { apiRequest } from "./api";

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  profile_complete: boolean;
  is_admin?: boolean;
}

export interface RegisterResponse {
  message: string;
}

export interface RegisterInput {
  email: string;
  full_name: string;
  password: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface GoogleLoginInput {
  credential: string;
}

export interface Profile {
  id: number;
  email: string;
  full_name: string;
  age: number | null;
  state: string | null;
  district: string | null;
  area_type: string | null;
  occupation: string | null;
  occupation_other: string | null;
  employment_status: string | null;
  worker_category: string | null;
  education_level: string | null;
  current_student: boolean | null;
  qualification: string | null;
  field_of_study: string | null;
  years_experience: number | null;
  preferred_job_roles: string[];
  preferred_job_states: string[];
  annual_income_range: string | null;
  household_size: number | null;
  beneficiary_categories: string[];
  profile_complete: boolean;
}

export type ProfileInput = Partial<
  Omit<Profile, "id" | "email" | "profile_complete">
>;

export interface EmailInput {
  email: string;
}

export interface TokenInput {
  token: string;
}

export interface PasswordResetInput extends TokenInput {
  new_password: string;
}

export interface MessageResponse {
  message: string;
}

export interface DevelopmentEmailResponse {
  purpose: string;
  token: string;
}

export interface EmailDeliveryStatusResponse {
  development_inbox_available: boolean;
}

export const authService = {
  getCurrentUser: () => apiRequest<AuthUser>("/auth/me"),
  register: (input: RegisterInput) =>
    apiRequest<RegisterResponse>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  login: (input: LoginInput) =>
    apiRequest<AuthUser>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  googleLogin: (input: GoogleLoginInput) =>
    apiRequest<AuthUser>("/auth/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  logout: () =>
    apiRequest<void>("/auth/logout", {
      method: "POST",
    }),
  verifyEmail: (input: TokenInput) =>
    apiRequest<MessageResponse>("/auth/verify-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  resendVerification: (input: EmailInput) =>
    apiRequest<MessageResponse>("/auth/resend-verification", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  forgotPassword: (input: EmailInput) =>
    apiRequest<MessageResponse>("/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  resetPassword: (input: PasswordResetInput) =>
    apiRequest<MessageResponse>("/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  getDevelopmentEmail: (email: string, purpose: string) =>
    apiRequest<DevelopmentEmailResponse>(
      `/auth/dev-email?email=${encodeURIComponent(email)}&purpose=${encodeURIComponent(purpose)}`,
    ),
  getEmailDeliveryStatus: () =>
    apiRequest<EmailDeliveryStatusResponse>("/auth/email-delivery-status"),
  getProfile: () => apiRequest<Profile>("/profile"),
  updateProfile: (input: ProfileInput) =>
    apiRequest<Profile>("/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
};
