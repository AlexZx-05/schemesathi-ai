import {
  ArrowRight,
  Bookmark,
  Bot,
  Bell,
  BriefcaseBusiness,
  CircleHelp,
  Compass,
  Home,
  ShieldCheck,
  Settings,
  UserRound,
} from "lucide-react";
import { Link, NavLink } from "react-router-dom";

import { useSavedSchemes } from "../../context/SavedSchemesContext";
import { useAuth } from "../../context/AuthContext";

export function DashboardSidebar() {
  const { savedSchemeIds } = useSavedSchemes();
  const { user } = useAuth();

  return (
    <aside aria-label="Dashboard navigation" className="dashboard-sidebar">
      <Link
        aria-label="SchemeSathi AI dashboard"
        className="dashboard-brand"
        to="/dashboard"
      >
        <img alt="" height="38" src="/images/Indian.png" width="38" />
        <span>
          <strong>SchemeSathi AI</strong>
          <span>Your scheme guide</span>
        </span>
      </Link>
      <div className="dashboard-sidebar-label">Workspace</div>
      <nav className="dashboard-side-nav">
        <NavLink className="dashboard-side-link" end to="/dashboard">
          <Home aria-hidden="true" size={18} />
          Dashboard
        </NavLink>
        <NavLink className="dashboard-side-link" to="/schemes">
          <Compass aria-hidden="true" size={18} />
          Discover schemes
        </NavLink>
        <NavLink className="dashboard-side-link" to="/jobs">
          <BriefcaseBusiness aria-hidden="true" size={18} />
          Government jobs
        </NavLink>
        <NavLink className="dashboard-side-link" to="/assistant">
          <Bot aria-hidden="true" size={18} />
          AI assistant
        </NavLink>
        <NavLink className="dashboard-side-link" to="/saved-schemes">
          <Bookmark aria-hidden="true" size={18} />
          Saved schemes
          {savedSchemeIds.length > 0 && (
            <span className="dashboard-nav-count">{savedSchemeIds.length}</span>
          )}
        </NavLink>
        <NavLink className="dashboard-side-link" to="/notifications">
          <Bell aria-hidden="true" size={18} />
          Notifications
        </NavLink>
        <NavLink className="dashboard-side-link" to="/settings">
          <Settings aria-hidden="true" size={18} />
          Notification settings
        </NavLink>
        <NavLink className="dashboard-side-link" to="/profile">
          <UserRound aria-hidden="true" size={18} />
          Your profile
        </NavLink>
        {user?.is_admin && (
          <>
            <NavLink className="dashboard-side-link" to="/admin">
              <ShieldCheck aria-hidden="true" size={18} />
              Admin dashboard
            </NavLink>
            <NavLink className="dashboard-side-link" to="/admin/jobs">
              <BriefcaseBusiness aria-hidden="true" size={18} />
              Manage job notices
            </NavLink>
          </>
        )}
      </nav>

      <div className="dashboard-help-card">
        <span className="dashboard-help-icon">
          <CircleHelp aria-hidden="true" size={19} />
        </span>
        <h2>Need a hand?</h2>
        <p>Learn how SchemeSathi works and where to verify information.</p>
        <Link to="/about">
          About this service <ArrowRight aria-hidden="true" size={14} />
        </Link>
      </div>
    </aside>
  );
}
