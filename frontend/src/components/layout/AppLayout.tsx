import { useState } from "react";
import { ChevronDown, Globe2, LogOut, Menu, X } from "lucide-react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../../context/AuthContext";
import { DashboardSidebar } from "./DashboardSidebar";

const navigation = [
  { label: "Home", to: "/" },
  { label: "Schemes", to: "/schemes" },
  { label: "Jobs", to: "/jobs" },
  { label: "About", to: "/about" },
];

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { logout, status, user } = useAuth();
  const pathname = useLocation().pathname;
  const isProfilePage = pathname === "/profile";
  const isOnboardingPage = pathname.startsWith("/onboarding/");
  const isDashboardPage = pathname === "/dashboard";
  const isAuthPage = [
    "/login",
    "/signup",
    "/register",
    "/verify-email",
    "/forgot-password",
    "/reset-password",
  ].includes(pathname);
  const isWorkspacePage =
    status === "authenticated" &&
    !isAuthPage &&
    !isOnboardingPage &&
    !isDashboardPage;
  const visibleNavigation =
    status === "authenticated"
      ? [
          { label: "Dashboard", to: "/dashboard" },
          { label: "Assistant", to: "/assistant" },
          { label: "Saved", to: "/saved-schemes" },
          { label: "Notifications", to: "/notifications" },
          { label: "Settings", to: "/settings" },
          ...(user?.is_admin ? [{ label: "Admin", to: "/admin" }] : []),
          ...navigation,
        ]
      : navigation;
  const pageTitle =
    pathname === "/assistant"
      ? "AI assistant"
      : pathname === "/saved-schemes"
        ? "Saved schemes"
        : pathname === "/profile"
          ? "Your profile"
          : pathname === "/notifications"
            ? "Notifications"
            : pathname === "/settings"
              ? "Notification settings"
              : pathname.startsWith("/jobs")
                ? "Government jobs"
              : pathname.startsWith("/admin")
                ? "Admin dashboard"
                : pathname.startsWith("/schemes/")
                  ? "Scheme details"
                  : pathname === "/schemes"
                    ? "Discover schemes"
                    : pathname === "/about"
                      ? "About this service"
                      : pathname.startsWith("/applications")
                        ? "Applications"
                        : "Workspace";
  const [logoutError, setLogoutError] = useState<string | null>(null);

  async function handleLogout() {
    setLogoutError(null);
    try {
      await logout();
      setMenuOpen(false);
    } catch (error) {
      setLogoutError(
        error instanceof Error
          ? error.message
          : "We couldn’t sign you out. Please try again.",
      );
    }
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      {!isDashboardPage && !isWorkspacePage && (
        <header
          className={`site-header${isAuthPage ? "site-header--auth" : ""}`}
        >
          <div className="header-inner">
            <Link
              aria-label="SchemeSathi AI home"
              className="brand"
              onClick={() => setMenuOpen(false)}
              to="/"
            >
              <img
                alt=""
                className="brand-mark-image"
                height="42"
                src="/images/Indian.png"
                width="42"
              />
              <span className="brand-copy">
                <span className="brand-name">SchemeSathi AI</span>
                <span className="brand-tagline">
                  Your Guide to Government Opportunities
                </span>
              </span>
            </Link>

            <button
              aria-expanded={menuOpen}
              aria-label={
                menuOpen ? "Close navigation menu" : "Open navigation menu"
              }
              aria-controls="main-navigation"
              className="menu-toggle"
              onClick={() => setMenuOpen((open) => !open)}
              type="button"
            >
              {menuOpen ? (
                <X aria-hidden="true" />
              ) : (
                <Menu aria-hidden="true" />
              )}
            </button>

            <nav
              aria-label="Main navigation"
              className={`site-nav ${menuOpen ? "site-nav--open" : ""}`}
              id="main-navigation"
            >
              {visibleNavigation.map(({ label, to }) => (
                <NavLink
                  key={to}
                  className={({ isActive }) =>
                    `nav-link${isActive ? "nav-link--active" : ""}`
                  }
                  onClick={() => setMenuOpen(false)}
                  to={to}
                >
                  {label}
                </NavLink>
              ))}
              <a
                className="nav-link"
                href="/#faq"
                onClick={() => setMenuOpen(false)}
              >
                FAQ
              </a>
              <button
                aria-describedby="language-coming-soon"
                className="language-control"
                disabled
                type="button"
              >
                <Globe2 aria-hidden="true" size={15} />
                English
                <ChevronDown aria-hidden="true" size={14} />
              </button>
              <span className="visually-hidden" id="language-coming-soon">
                Language selection is coming soon.
              </span>
              {!isAuthPage &&
                !isWorkspacePage &&
                !isProfilePage &&
                !isOnboardingPage &&
                !isDashboardPage && (
                  <span className="header-auth-control">
                    {status === "authenticated" ? (
                      <>
                        <Link
                          className="header-login header-account-link"
                          onClick={() => setMenuOpen(false)}
                          to="/profile"
                        >
                          {user?.full_name.split(" ")[0] ?? "Profile"}
                        </Link>
                        <button
                          className="header-signup header-logout"
                          onClick={handleLogout}
                          type="button"
                        >
                          Sign out
                        </button>
                      </>
                    ) : status === "loading" ? null : (
                      <>
                        <Link
                          className="header-login"
                          onClick={() => setMenuOpen(false)}
                          to="/login"
                        >
                          Login
                        </Link>
                        <Link
                          className="header-signup"
                          onClick={() => setMenuOpen(false)}
                          to="/signup"
                        >
                          Sign Up
                        </Link>
                      </>
                    )}
                  </span>
                )}
              {logoutError && (
                <span className="header-logout-error" role="alert">
                  {logoutError}
                </span>
              )}
            </nav>
          </div>
        </header>
      )}

      <main className="main-content" id="main-content">
        {isWorkspacePage ? (
          <div className="dashboard-shell">
            <DashboardSidebar />
            <section className="dashboard-content">
              <div className="dashboard-topbar">
                <p>{pageTitle}</p>
                <Link
                  aria-label="View your profile"
                  className="dashboard-avatar"
                  to="/profile"
                >
                  {user?.full_name.trim().charAt(0).toUpperCase() || "U"}
                </Link>
                <button
                  aria-label="Sign out"
                  className="dashboard-signout"
                  onClick={handleLogout}
                  type="button"
                >
                  <LogOut aria-hidden="true" size={16} />
                  <span>Sign out</span>
                </button>
              </div>
              {logoutError && (
                <p className="dashboard-logout-error" role="alert">
                  {logoutError}
                </p>
              )}
              <Outlet />
            </section>
          </div>
        ) : (
          <Outlet />
        )}
      </main>

      {!isAuthPage &&
        !isProfilePage &&
        !isOnboardingPage &&
        !isDashboardPage && (
          <footer className="site-footer">
            <div className="footer-inner">
              <span>SchemeSathi AI · An independent civic-tech project</span>
              <p>
                Information is for general guidance only. Always verify details
                with the relevant official source.
              </p>
            </div>
          </footer>
        )}
    </div>
  );
}
