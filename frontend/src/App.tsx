import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
import { AboutPage } from "./pages/AboutPage";
import { HomePage } from "./pages/HomePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SchemeDetailsPage } from "./pages/SchemeDetailsPage";
import { EligibilityAssessmentPage } from "./pages/EligibilityAssessmentPage";
import { SchemesPage } from "./pages/SchemesPage";
import { SavedSchemesProvider } from "./context/SavedSchemesContext";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import { ProfilePage } from "./pages/ProfilePage";
import { RegisterPage } from "./pages/RegisterPage";
import {
  ForgotPasswordPage,
  ResetPasswordPage,
  VerifyEmailPage,
} from "./pages/AuthWorkflowPages";
import { OnboardingPage } from "./pages/OnboardingPage";
import { DashboardPage } from "./pages/DashboardPage";
import { AssistantPage } from "./pages/AssistantPage";
import {
  ApplicationDetailPage,
  ApplicationsPage,
  ApplyPage,
  DocumentsPage,
  SavedSchemesPage,
} from "./pages/GuidancePages";
import { useAuth } from "./context/AuthContext";
import {
  NotificationsPage,
  NotificationSettingsPage,
} from "./pages/NotificationsPage";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { JobsPage } from "./pages/JobsPage";
import { JobDetailsPage } from "./pages/JobDetailsPage";
import { AdminJobsPage } from "./pages/AdminJobsPage";

function RootPage() {
  const { status, user } = useAuth();

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

  if (status === "authenticated") {
    return (
      <Navigate
        replace
        to={user?.profile_complete ? "/dashboard" : "/onboarding/welcome"}
      />
    );
  }

  return <HomePage />;
}

export function AppRoutes() {
  return (
    <AuthProvider>
      <SavedSchemesProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<RootPage />} />
            <Route path="schemes" element={<SchemesPage />} />
            <Route path="jobs" element={<JobsPage />} />
            <Route path="jobs/:jobSlug" element={<JobDetailsPage />} />
            <Route element={<ProtectedRoute />}>
              <Route
                path="schemes/:schemeId/eligibility-check"
                element={<EligibilityAssessmentPage />}
              />
            </Route>
            <Route path="schemes/:schemeId" element={<SchemeDetailsPage />} />
            <Route path="about" element={<AboutPage />} />
            <Route element={<ProtectedRoute />}>
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="assistant" element={<AssistantPage />} />
              <Route path="saved-schemes" element={<SavedSchemesPage />} />
              <Route
                path="schemes/:schemeId/documents"
                element={<DocumentsPage />}
              />
              <Route path="schemes/:schemeId/apply" element={<ApplyPage />} />
              <Route path="applications" element={<ApplicationsPage />} />
              <Route
                path="applications/:applicationId"
                element={<ApplicationDetailPage />}
              />
              <Route path="notifications" element={<NotificationsPage />} />
              <Route path="settings" element={<NotificationSettingsPage />} />
              <Route path="admin" element={<AdminDashboardPage />} />
              <Route path="admin/jobs" element={<AdminJobsPage />} />
            </Route>
            <Route path="login" element={<LoginPage />} />
            <Route path="signup" element={<RegisterPage />} />
            <Route path="register" element={<RegisterPage />} />
            <Route path="verify-email" element={<VerifyEmailPage />} />
            <Route path="forgot-password" element={<ForgotPasswordPage />} />
            <Route path="reset-password" element={<ResetPasswordPage />} />
            <Route element={<ProtectedRoute />}>
              <Route path="onboarding/:step" element={<OnboardingPage />} />
              <Route path="profile" element={<ProfilePage />} />
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </SavedSchemesProvider>
    </AuthProvider>
  );
}
