import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../../context/AuthContext";

export function ProtectedRoute() {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div aria-live="polite" className="auth-loading">
        Checking your sign-in…
      </div>
    );
  }

  if (status === "error") {
    return (
      <section aria-labelledby="auth-session-error" className="auth-page">
        <div className="auth-card auth-card--notice" role="alert">
          <h1 id="auth-session-error">Couldn’t check your session</h1>
          <p>Refresh the page or try again when the service is available.</p>
        </div>
      </section>
    );
  }

  if (status !== "authenticated") {
    const next = `${location.pathname}${location.search}`;
    return <Navigate replace state={{ from: next }} to="/login" />;
  }

  const isOnboardingRoute = location.pathname.startsWith("/onboarding/");
  const isEligibilityAssessmentRoute = /^\/schemes\/[^/]+\/eligibility-check$/.test(
    location.pathname,
  );
  if (
    !user?.profile_complete &&
    !isOnboardingRoute &&
    !isEligibilityAssessmentRoute
  ) {
    return <Navigate replace to="/onboarding/welcome" />;
  }
  if (user?.profile_complete && isOnboardingRoute) {
    return <Navigate replace to="/dashboard" />;
  }

  return <Outlet />;
}
