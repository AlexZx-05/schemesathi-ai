import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  Smartphone,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { useAuth } from "../context/AuthContext";
import { GoogleSignInButton } from "../components/auth/GoogleSignInButton";
import { TextField } from "../components/ui/TextField";
import { ApiError } from "../lib/api";

const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
});

type LoginValues = z.infer<typeof loginSchema>;

const loginHighlights = [
  {
    icon: UserRound,
    title: "Explore schemes",
    description: "Browse source-linked records",
  },
  {
    icon: CheckCircle2,
    title: "Manage your profile",
    description: "Keep your details up to date",
  },
  {
    icon: BookOpenCheck,
    title: "Verify before you apply",
    description: "Confirm details with official sources",
  },
];

export function LoginPage() {
  const { googleLogin, login, status, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [googleSubmitting, setGoogleSubmitting] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  if (status === "authenticated") {
    return (
      <Navigate
        replace
        to={user?.profile_complete ? "/dashboard" : "/onboarding/welcome"}
      />
    );
  }

  async function onSubmit(values: LoginValues) {
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      const signedInUser = await login(values);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(
        from ??
          (signedInUser.profile_complete ? "/dashboard" : "/onboarding/welcome"),
        { replace: true },
      );
    } catch (error) {
      if (error instanceof ApiError && error.status === 403) {
        navigate(`/verify-email?email=${encodeURIComponent(values.email)}`, {
          replace: true,
        });
        return;
      }
      setSubmitError(
        error instanceof Error
          ? error.message
          : "We couldn’t sign you in. Please try again.",
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
      const from = (location.state as { from?: string } | null)?.from;
      navigate(
        from ??
          (signedInUser.profile_complete ? "/dashboard" : "/onboarding/welcome"),
        { replace: true },
      );
    } catch (error) {
      setSubmitError(
        error instanceof Error
          ? error.message
          : "We couldn’t sign you in with Google. Please try again.",
      );
    } finally {
      setGoogleSubmitting(false);
    }
  }

  return (
    <section
      aria-labelledby="login-title"
      className="auth-page auth-page--login"
    >
      <div className="auth-visual">
        <div
          aria-label="Indian students and a farmer with the Parliament, India Gate, fields, and the national flag"
          className="auth-hero-image"
          role="img"
        />
        <div className="auth-visual-copy">
          <p className="auth-visual-eyebrow">
            India’s government schemes, made simple
          </p>
          <h2>
            Welcome to
            <span>SchemeSathi AI</span>
          </h2>
          <p className="auth-visual-description">
            One place to explore schemes, manage your profile, and plan
            your next step with confidence.
          </p>
          <ul aria-label="What you can do" className="auth-highlights">
            {loginHighlights.map(({ description, icon: Icon, title }) => (
              <li key={title}>
                <span className="auth-highlight-icon">
                  <Icon aria-hidden="true" size={18} />
                </span>
                <span className="auth-highlight-copy">
                  <strong>{title}</strong>
                  <span>{description}</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="auth-visual-disclaimer">
            SchemeSathi AI is an independent civic-tech project, not a
            government service.
          </p>
        </div>
      </div>

      <div className="auth-card auth-login-card">
        <div className="auth-login-brand">
          <img alt="" height="44" src="/images/Indian.png" width="44" />
          <span className="auth-login-brand-copy">
            <strong>SchemeSathi AI</strong>
            <span>Your Guide to Government Opportunities</span>
          </span>
        </div>
        <h1
          aria-label="Sign in to SchemeSathi"
          className="page-title"
          id="login-title"
        >
          Welcome Back
        </h1>
        <p className="page-intro">Log in to continue to your account</p>
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
        <form className="auth-form" onSubmit={handleSubmit(onSubmit)}>
          <div className="auth-input-with-icon">
            <Mail aria-hidden="true" className="auth-input-icon" size={18} />
            <TextField
              autoComplete="email"
              error={errors.email?.message}
              id="login-email"
              label="Email address"
              placeholder="you@example.com"
              required
              type="email"
              {...register("email")}
            />
          </div>
          <div className="auth-password-group">
            <div className="auth-input-with-icon">
              <LockKeyhole
                aria-hidden="true"
                className="auth-input-icon"
                size={18}
              />
              <TextField
                autoComplete="current-password"
                error={errors.password?.message}
                id="login-password"
                label="Password"
                placeholder="Enter your password"
                required
                type={passwordVisible ? "text" : "password"}
                {...register("password")}
              />
              <button
                aria-label={passwordVisible ? "Hide password" : "Show password"}
                aria-pressed={passwordVisible}
                className="auth-password-toggle"
                onClick={() => setPasswordVisible((visible) => !visible)}
                type="button"
              >
                {passwordVisible ? (
                  <EyeOff aria-hidden="true" size={18} />
                ) : (
                  <Eye aria-hidden="true" size={18} />
                )}
              </button>
            </div>
            <Link className="auth-recovery-link" to="/forgot-password">
              Forgot password?
            </Link>
          </div>
          <button
            aria-label="Sign in"
            className="button button--primary auth-submit"
            disabled={isSubmitting || googleSubmitting}
            type="submit"
          >
            {isSubmitting ? "Signing in…" : "Login"}
            {!isSubmitting && <ArrowRight aria-hidden="true" size={17} />}
          </button>
        </form>
        <div aria-hidden="true" className="auth-social-divider">
          <span>or continue with</span>
        </div>
        <div className="auth-social-options">
          <GoogleSignInButton
            disabled={isSubmitting || googleSubmitting}
            onCredential={onGoogleCredential}
          />
          <button
            aria-describedby="social-login-note"
            className="auth-social-button"
            disabled
            type="button"
          >
            <Smartphone aria-hidden="true" size={19} />
            Continue with Mobile Number
          </button>
        </div>
        <span className="visually-hidden" id="social-login-note">
          Mobile sign-in is not available yet.
        </span>
        <p className="auth-switch">
          Don’t have an account? <Link to="/signup">Sign Up</Link>
        </p>
      </div>
    </section>
  );
}
