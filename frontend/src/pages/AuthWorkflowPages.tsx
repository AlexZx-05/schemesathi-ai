import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { authService } from "../lib/auth";
import { ApiError } from "../lib/api";

function WorkflowFrame({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section aria-labelledby="workflow-title" className="workflow-page">
      <div className="workflow-card">
        <h1 id="workflow-title">{title}</h1>
        {children}
      </div>
    </section>
  );
}

function useDevelopmentInboxAvailability() {
  const [available, setAvailable] = useState(false);

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    let mounted = true;
    authService
      .getEmailDeliveryStatus()
      .then((status) => {
        if (mounted) setAvailable(status.development_inbox_available);
      })
      .catch(() => {
        if (mounted) setAvailable(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  return available;
}

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const initialToken = searchParams.get("token") ?? "";
  const [email, setEmail] = useState(searchParams.get("email") ?? "");
  const [token, setToken] = useState(initialToken);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const developmentInboxAvailable = useDevelopmentInboxAvailability();

  useEffect(() => {
    if (!initialToken) return;
    let mounted = true;
    setBusy(true);
    authService
      .verifyEmail({ token: initialToken })
      .then((result) => {
        if (mounted) setMessage(result.message);
      })
      .catch((requestError: unknown) => {
        if (mounted) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "We could not verify this link.",
          );
        }
      })
      .finally(() => {
        if (mounted) setBusy(false);
      });
    return () => {
      mounted = false;
    };
  }, [initialToken]);

  async function submitVerification(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await authService.verifyEmail({ token });
      setMessage(result.message);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "We could not verify this link.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function resendVerification() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await authService.resendVerification({ email });
      setMessage(result.message);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Try again later.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function loadDevelopmentToken() {
    setBusy(true);
    setError(null);
    try {
      const delivery = await authService.getDevelopmentEmail(
        email,
        "verification",
      );
      setToken(delivery.token);
      setMessage(
        "Development email loaded. Submit the token to verify your address.",
      );
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.status === 404
          ? "No development email is available. This inbox is enabled only for local development."
          : requestError instanceof Error
            ? requestError.message
            : "Could not read the development email inbox.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <WorkflowFrame title="Verify your email">
      <p>
        {email
          ? `We sent a verification link to ${email}. Open it to enable password sign-in.`
          : "Confirm your email address to enable password sign-in."}
      </p>
      {message && (
        <p className="workflow-success" role="status">
          {message}
        </p>
      )}
      {error && (
        <p className="form-error-banner" role="alert">
          {error}
        </p>
      )}
      {!initialToken && (
        <>
          <form className="workflow-form" onSubmit={submitVerification}>
            <label htmlFor="verification-token">Verification token</label>
            <input
              autoComplete="one-time-code"
              id="verification-token"
              onChange={(event) => setToken(event.target.value)}
              required
              value={token}
            />
            <button
              className="button button--primary"
              disabled={busy || !token}
              type="submit"
            >
              {busy ? "Verifying…" : "Verify email"}
            </button>
          </form>
          <div className="workflow-actions">
            <label htmlFor="verification-email">Email address</label>
            <input
              autoComplete="email"
              id="verification-email"
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              value={email}
            />
            <button
              className="button button--secondary"
              disabled={busy || !email}
              onClick={resendVerification}
              type="button"
            >
              Resend verification email
            </button>
            {developmentInboxAvailable && (
              <button
                className="button button--secondary"
                disabled={busy || !email}
                onClick={loadDevelopmentToken}
                type="button"
              >
                Read local development inbox
              </button>
            )}
          </div>
        </>
      )}
      <p className="workflow-links">
        <Link to="/login">Return to login</Link>
      </p>
    </WorkflowFrame>
  );
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [developmentToken, setDevelopmentToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const developmentInboxAvailable = useDevelopmentInboxAvailability();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      setMessage((await authService.forgotPassword({ email })).message);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Try again later.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function loadDevelopmentReset() {
    setBusy(true);
    setError(null);
    setDevelopmentToken(null);
    try {
      const delivery = await authService.getDevelopmentEmail(
        email,
        "password_reset",
      );
      setDevelopmentToken(delivery.token);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.status === 404
          ? "No development email is available. This inbox is enabled only for local development."
          : requestError instanceof Error
            ? requestError.message
            : "Could not read the development email inbox.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <WorkflowFrame title="Reset your password">
      <p>
        Enter your email. If an account is associated with it, we’ll send reset
        instructions.
      </p>
      {message && (
        <p className="workflow-success" role="status">
          {message}
        </p>
      )}
      {error && (
        <p className="form-error-banner" role="alert">
          {error}
        </p>
      )}
      <form className="workflow-form" onSubmit={submit}>
        <label htmlFor="forgot-email">Email address</label>
        <input
          autoComplete="email"
          id="forgot-email"
          onChange={(event) => setEmail(event.target.value)}
          required
          type="email"
          value={email}
        />
        <button
          className="button button--primary"
          disabled={busy}
          type="submit"
        >
          {busy ? "Sending…" : "Send reset instructions"}
        </button>
      </form>
      {developmentInboxAvailable && (
        <button
          className="button button--secondary"
          disabled={busy || !email}
          onClick={loadDevelopmentReset}
          type="button"
        >
          Read local development inbox
        </button>
      )}
      {developmentInboxAvailable && developmentToken && (
        <p className="workflow-success" role="status">
          Development email loaded.{" "}
          <Link
            to={`/reset-password?token=${encodeURIComponent(developmentToken)}`}
          >
            Continue to password reset
          </Link>
        </p>
      )}
      <p className="workflow-links">
        <Link to="/login">Return to login</Link>
      </p>
    </WorkflowFrame>
  );
}

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      setMessage(
        (
          await authService.resetPassword({
            token,
            new_password: password,
          })
        ).message,
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Try again later.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <WorkflowFrame title="Choose a new password">
      <p>Use at least 12 characters. Reset links expire after one hour.</p>
      {!token && (
        <p className="form-error-banner" role="alert">
          The reset link is missing. Request a new one.
        </p>
      )}
      {message && (
        <p className="workflow-success" role="status">
          {message}
        </p>
      )}
      {error && (
        <p className="form-error-banner" role="alert">
          {error}
        </p>
      )}
      {token && !message && (
        <form className="workflow-form" onSubmit={submit}>
          <label htmlFor="reset-password">New password</label>
          <input
            autoComplete="new-password"
            id="reset-password"
            minLength={12}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
          <button
            className="button button--primary"
            disabled={busy}
            type="submit"
          >
            {busy ? "Saving…" : "Reset password"}
          </button>
        </form>
      )}
      <p className="workflow-links">
        <Link to="/login">Return to login</Link>
      </p>
    </WorkflowFrame>
  );
}
