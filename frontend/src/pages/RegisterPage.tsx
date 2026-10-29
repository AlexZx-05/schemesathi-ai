import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowRight,
  BookOpenCheck,
  Check,
  Eye,
  EyeOff,
  Files,
  Home,
  LockKeyhole,
  Mail,
  Sprout,
  BriefcaseBusiness,
  UserRound,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";

import { GoogleSignInButton } from "../components/auth/GoogleSignInButton";
import { TextField } from "../components/ui/TextField";
import { useAuth } from "../context/AuthContext";

const registerSchema = z
  .object({
    full_name: z
      .string()
      .trim()
      .min(2, "Enter your name.")
      .max(100, "Name must be 100 characters or fewer."),
    email: z.string().trim().email("Enter a valid email address."),
    password: z
      .string()
      .min(12, "Use at least 12 characters.")
      .max(128, "Password must be 128 characters or fewer."),
    confirm_password: z.string(),
  })
  .refine((values) => values.password === values.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });

type RegisterValues = z.infer<typeof registerSchema>;

const signupBenefits = [
  {
    icon: UserRound,
    title: "Personalized recommendations",
    description: "Find scheme information that matches your profile.",
    tone: "mint",
  },
  {
    icon: Files,
    title: "Step-by-step guidance",
    description: "Understand criteria, documents, and how to apply.",
    tone: "lavender",
  },
  {
    icon: ShieldCheck,
    title: "Trusted information",
    description: "Confirm details with official government sources.",
    tone: "blue",
  },
] as const;

const opportunityCategories = [
  { icon: BookOpenCheck, title: "Scholarships", description: "for students" },
  {
    icon: BriefcaseBusiness,
    title: "Employment",
    description: "opportunities",
  },
  { icon: Home, title: "Housing", description: "assistance" },
  { icon: Sprout, title: "Farmer", description: "programs" },
] as const;

export function RegisterPage() {
  const { googleLogin, register: createAccount, status, user } = useAuth();
  const navigate = useNavigate();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [googleSubmitting, setGoogleSubmitting] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [confirmationVisible, setConfirmationVisible] = useState(false);
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: "",
      email: "",
      password: "",
      confirm_password: "",
    },
  });

  const password = watch("password");

  if (status === "authenticated") {
    return (
      <Navigate
        replace
        to={user?.profile_complete ? "/dashboard" : "/onboarding/welcome"}
      />
    );
  }

  async function onSubmit(values: RegisterValues) {
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      await createAccount({
        full_name: values.full_name,
        email: values.email,
        password: values.password,
      });
      navigate(`/verify-email?email=${encodeURIComponent(values.email)}`, {
        replace: true,
      });
    } catch (error) {
      setSubmitError(
        error instanceof Error
          ? error.message
          : "We couldn’t create your account. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function onGoogleCredential(credential: string) {
    setSubmitError(null);
    setGoogleSubmitting(true);
    try {
      const signedInUser = await googleLogin({ credential });
      navigate(
        signedInUser.profile_complete ? "/dashboard" : "/onboarding/welcome",
        { replace: true },
      );
    } catch (error) {
      setSubmitError(
        error instanceof Error
          ? error.message
          : "We couldn’t create your account with Google. Please try again.",
      );
    } finally {
      setGoogleSubmitting(false);
    }
  }

  return (
    <section
      aria-labelledby="register-title"
      className="auth-page auth-page--register"
    >
      <div className="signup-visual">
        <div
          aria-label="A student in front of the Indian Parliament and India Gate"
          className="signup-hero-art"
          role="img"
        />
        <div className="signup-hero-copy">
          <p className="signup-hero-badge">
            <BookOpenCheck aria-hidden="true" size={17} />
            AI-Powered Government Scheme Assistant
          </p>
          <h1>
            Create Your Account
            <span>and Unlock</span>
            <span>New Opportunities</span>
          </h1>
          <p className="signup-hero-description">
            Discover scheme information, understand preliminary eligibility, and
            find official application guidance — all in one place.
          </p>

          <ul aria-label="Why create an account" className="signup-benefits">
            {signupBenefits.map(({ description, icon: Icon, title, tone }) => (
              <li key={title}>
                <span className={`signup-benefit-icon is-${tone}`}>
                  <Icon aria-hidden="true" size={21} />
                </span>
                <span>
                  <strong>{title}</strong>
                  <span>{description}</span>
                </span>
              </li>
            ))}
          </ul>

          <div
            aria-label="Types of opportunities"
            className="signup-category-cards"
          >
            {opportunityCategories.map(
              ({ description, icon: Icon, title }, index) => (
                <div
                  className={`signup-category-card card-${index + 1}`}
                  key={title}
                >
                  <span className={`signup-category-icon tone-${index + 1}`}>
                    <Icon aria-hidden="true" size={18} />
                  </span>
                  <span>
                    <strong>{title}</strong>
                    <span>{description}</span>
                  </span>
                </div>
              ),
            )}
          </div>
          <p className="signup-visual-disclaimer">
            An independent civic-tech project, not a government service.
          </p>
        </div>
      </div>

      <div className="auth-card signup-card">
        <div className="signup-brand">
          <img alt="" height="42" src="/images/Indian.png" width="42" />
          <span>
            <strong>SchemeSathi AI</strong>
            <span>Your Guide to Government Opportunities</span>
          </span>
        </div>
        <header className="signup-heading">
          <h2 id="register-title">Create Your Account</h2>
          <p>Join SchemeSathi AI to explore government schemes</p>
        </header>

        {status === "error" && (
          <p className="form-error-banner" role="alert">
            The authentication service is currently unavailable. Please check
            the API connection and try again.
          </p>
        )}
        {submitError && (
          <p className="form-error-banner" role="alert">
            {submitError}
          </p>
        )}

        <form
          className="auth-form signup-form"
          noValidate
          onSubmit={handleSubmit(onSubmit)}
        >
          <div className="signup-input-with-icon">
            <UserRound
              aria-hidden="true"
              className="signup-input-icon"
              size={17}
            />
            <TextField
              autoComplete="name"
              error={errors.full_name?.message}
              id="register-name"
              label="Full name"
              placeholder="Enter your full name"
              required
              {...register("full_name")}
            />
          </div>
          <div className="signup-input-with-icon">
            <Mail aria-hidden="true" className="signup-input-icon" size={17} />
            <TextField
              autoComplete="email"
              error={errors.email?.message}
              id="register-email"
              label="Email address"
              placeholder="Enter your email address"
              required
              type="email"
              {...register("email")}
            />
          </div>
          <div className="signup-password-group">
            <div className="signup-input-with-icon">
              <LockKeyhole
                aria-hidden="true"
                className="signup-input-icon"
                size={17}
              />
              <TextField
                autoComplete="new-password"
                error={errors.password?.message}
                id="register-password"
                label="Password"
                placeholder="Create a password"
                required
                type={passwordVisible ? "text" : "password"}
                {...register("password")}
              />
              <button
                aria-label={passwordVisible ? "Hide password" : "Show password"}
                aria-pressed={passwordVisible}
                className="signup-password-toggle"
                onClick={() => setPasswordVisible((visible) => !visible)}
                type="button"
              >
                {passwordVisible ? (
                  <EyeOff aria-hidden="true" size={17} />
                ) : (
                  <Eye aria-hidden="true" size={17} />
                )}
              </button>
            </div>
            <p className="signup-password-hint">
              <Check aria-hidden="true" size={13} />
              Use at least 12 characters.
              {password.length >= 12 && (
                <span className="signup-password-valid">Requirement met</span>
              )}
            </p>
          </div>
          <div className="signup-input-with-icon">
            <LockKeyhole
              aria-hidden="true"
              className="signup-input-icon"
              size={17}
            />
            <TextField
              autoComplete="new-password"
              error={errors.confirm_password?.message}
              id="register-confirm-password"
              label="Confirm password"
              placeholder="Confirm your password"
              required
              type={confirmationVisible ? "text" : "password"}
              {...register("confirm_password")}
            />
            <button
              aria-label={
                confirmationVisible ? "Hide confirmation" : "Show confirmation"
              }
              aria-pressed={confirmationVisible}
              className="signup-password-toggle"
              onClick={() => setConfirmationVisible((visible) => !visible)}
              type="button"
            >
              {confirmationVisible ? (
                <EyeOff aria-hidden="true" size={17} />
              ) : (
                <Eye aria-hidden="true" size={17} />
              )}
            </button>
          </div>
          <button
            className="button button--primary auth-submit signup-submit"
            disabled={isSubmitting || googleSubmitting}
            type="submit"
          >
            {isSubmitting ? "Creating account…" : "Sign Up"}
            {!isSubmitting && <ArrowRight aria-hidden="true" size={17} />}
          </button>
        </form>

        <div aria-hidden="true" className="auth-social-divider">
          <span>or</span>
        </div>
        <div className="signup-social-actions">
          <GoogleSignInButton
            disabled={isSubmitting || googleSubmitting}
            onCredential={onGoogleCredential}
          />
        </div>
        <p className="auth-switch signup-auth-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
        <p className="signup-privacy-note">
          Never enter Aadhaar, bank account, government-portal passwords, or
          other sensitive numbers here.
        </p>
      </div>
    </section>
  );
}
