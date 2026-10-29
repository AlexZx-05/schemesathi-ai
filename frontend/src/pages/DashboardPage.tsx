import {
  ArrowRight,
  BriefcaseBusiness,
  Bookmark,
  CheckCircle2,
  FileSearch,
  LogOut,
  Search,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { DashboardSidebar } from "../components/layout/DashboardSidebar";
import { GovernmentJobCard } from "../components/jobs/GovernmentJobCard";
import { SchemeCard } from "../components/schemes/SchemeCard";
import { RecommendationCard } from "../components/schemes/RecommendationCard";
import { useAuth } from "../context/AuthContext";
import { useSavedSchemes } from "../context/SavedSchemesContext";
import { authService } from "../lib/auth";
import type { Profile } from "../lib/auth";
import { jobService } from "../lib/jobs";
import type { JobRecommendation } from "../lib/jobs";
import { schemeService } from "../lib/schemes/service";
import type {
  DashboardSummary,
  RecommendationPage,
} from "../lib/schemes/service";
import type { Scheme } from "../lib/schemes/types";

type LoadState = "loading" | "success" | "error";

export function DashboardPage() {
  const { logout, user } = useAuth();
  const { savedSchemeIds, storageError } = useSavedSchemes();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [recommendationPage, setRecommendationPage] =
    useState<RecommendationPage | null>(null);
  const [recommendationState, setRecommendationState] =
    useState<LoadState>("loading");
  const [recommendationError, setRecommendationError] = useState<string | null>(
    null,
  );
  const [jobRecommendations, setJobRecommendations] = useState<
    JobRecommendation[]
  >([]);
  const [jobRecommendationState, setJobRecommendationState] =
    useState<LoadState>("loading");
  const [jobRecommendationError, setJobRecommendationError] = useState<
    string | null
  >(null);
  const [dashboardSummary, setDashboardSummary] =
    useState<DashboardSummary | null>(null);
  const [summaryState, setSummaryState] = useState<LoadState>("loading");
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setLoadState("loading");
    setRecommendationState("loading");
    setJobRecommendationState("loading");
    setSummaryState("loading");
    setLoadError(null);
    setRecommendationError(null);
    setJobRecommendationError(null);
    setSummaryError(null);

    authService
      .getProfile()
      .then((loadedProfile) => {
        if (active) setProfile(loadedProfile);
      })
      .catch((error: unknown) => {
        if (active) {
          setProfileError(
            error instanceof Error
              ? error.message
              : "Your profile details could not be loaded.",
          );
        }
      });

    schemeService
      .getSchemes()
      .then((loadedSchemes) => {
        if (active) {
          setSchemes(loadedSchemes);
          setLoadState("success");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setLoadError(
            error instanceof Error
              ? error.message
              : "Scheme records could not be loaded.",
          );
          setLoadState("error");
        }
      });

    schemeService
      .getRecommendations()
      .then((result) => {
        if (active) {
          setRecommendationPage(result);
          setRecommendationState("success");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setRecommendationError(
            error instanceof Error
              ? error.message
              : "Personalized recommendations could not be loaded.",
          );
          setRecommendationState("error");
        }
      });

    jobService
      .getRecommendations()
      .then((result) => {
        if (active) {
          setJobRecommendations(result.items);
          setJobRecommendationState("success");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setJobRecommendationError(
            error instanceof Error
              ? error.message
              : "Government job matches could not be loaded.",
          );
          setJobRecommendationState("error");
        }
      });

    schemeService
      .getDashboardSummary()
      .then((result) => {
        if (active) {
          setDashboardSummary(result);
          setSummaryState("success");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setSummaryError(
            error instanceof Error
              ? error.message
              : "Your dashboard summary could not be loaded.",
          );
          setSummaryState("error");
        }
      });

    return () => {
      active = false;
    };
  }, [reloadKey]);

  const savedSchemes = useMemo(
    () => schemes.filter((scheme) => savedSchemeIds.includes(scheme.id)),
    [schemes, savedSchemeIds],
  );
  const firstName = user?.full_name.trim().split(/\s+/)[0] || "there";

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = searchQuery.trim();
    navigate(query ? `/schemes?q=${encodeURIComponent(query)}` : "/schemes");
  }

  async function handleLogout() {
    setLogoutError(null);
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch (error) {
      setLogoutError(
        error instanceof Error
          ? error.message
          : "We couldn’t sign you out. Please try again.",
      );
    }
  }

  return (
    <div className="dashboard-shell">
      <DashboardSidebar />

      <section aria-labelledby="dashboard-title" className="dashboard-content">
        <div className="dashboard-topbar">
          <p>Dashboard</p>
          <form
            aria-label="Search schemes"
            className="dashboard-search"
            onSubmit={handleSearch}
            role="search"
          >
            <Search aria-hidden="true" size={18} />
            <label className="visually-hidden" htmlFor="dashboard-search">
              Search the scheme catalogue
            </label>
            <input
              id="dashboard-search"
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search schemes by name or topic"
              type="search"
              value={searchQuery}
            />
            <button aria-label="Submit scheme search" type="submit">
              <ArrowRight aria-hidden="true" size={17} />
            </button>
          </form>
          <Link
            aria-label="View your profile"
            className="dashboard-avatar"
            to="/profile"
          >
            {firstName.slice(0, 1).toUpperCase()}
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

        <div className="dashboard-main">
          <section
            aria-labelledby="dashboard-title"
            className="dashboard-welcome"
          >
            <div className="dashboard-welcome-copy">
              <p className="eyebrow">Your SchemeSathi overview</p>
              <h1 id="dashboard-title">Welcome, {firstName}</h1>
              <p>
                Explore public-benefit information and keep your saved schemes
                close at hand.
              </p>
              <Link className="button button--primary" to="/schemes">
                Explore schemes
                <ArrowRight aria-hidden="true" size={16} />
              </Link>
              <Link className="dashboard-assistant-action" to="/assistant">
                AI assistant
              </Link>
            </div>
            <img
              alt=""
              className="dashboard-welcome-art"
              height="768"
              src="/images/scheme-opportunities-hero.png"
              width="1024"
            />
            <div className="dashboard-profile-summary">
              <span className="dashboard-profile-icon">
                <UserRound aria-hidden="true" size={20} />
              </span>
              <span className="dashboard-profile-copy">
                <strong>Your profile</strong>
                {profileError ? (
                  <span role="status">{profileError}</span>
                ) : profile ? (
                  <span>
                    {[
                      profile.age ? `${profile.age} years` : null,
                      profile.state,
                      profile.education_level,
                    ]
                      .filter(Boolean)
                      .join(" · ") || "Add details to your profile"}
                  </span>
                ) : (
                  <span>Loading profile details…</span>
                )}
              </span>
              <div
                aria-label={`Profile completion: ${recommendationPage?.completion_percentage ?? 0}%`}
                className="dashboard-profile-completion"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={recommendationPage?.completion_percentage ?? 0}
              >
                <div>
                  <span>Profile completion</span>
                  <strong>
                    {recommendationPage?.completion_percentage ?? 0}%
                  </strong>
                </div>
                <span className="dashboard-progress-track">
                  <span
                    style={{
                      width: `${recommendationPage?.completion_percentage ?? 0}%`,
                    }}
                  />
                </span>
              </div>
              <Link className="dashboard-profile-edit" to="/profile">
                Edit profile
              </Link>
            </div>
          </section>

          <section
            aria-label="Your activity at a glance"
            className="dashboard-stats"
          >
            <article className="dashboard-stat dashboard-stat--blue">
              <span className="dashboard-stat-icon">
                <FileSearch aria-hidden="true" size={20} />
              </span>
              <span className="dashboard-stat-label">Recommendations</span>
              <strong>
                {recommendationState === "success"
                  ? (recommendationPage?.total ?? 0)
                  : "—"}
              </strong>
              <a href="#recommendations">View recommendations</a>
            </article>
            <article className="dashboard-stat dashboard-stat--violet">
              <span className="dashboard-stat-icon">
                <Bookmark aria-hidden="true" size={20} />
              </span>
              <span className="dashboard-stat-label">Saved by you</span>
              <strong>{savedSchemes.length}</strong>
              <a href="#saved-schemes">View saved</a>
            </article>
            <article className="dashboard-stat dashboard-stat--green">
              <span className="dashboard-stat-icon">
                <CheckCircle2 aria-hidden="true" size={20} />
              </span>
              <span className="dashboard-stat-label">Profile complete</span>
              <strong>{recommendationPage?.completion_percentage ?? 0}%</strong>
              <Link to="/profile">Review details</Link>
            </article>
            <article className="dashboard-stat dashboard-stat--amber">
              <span className="dashboard-stat-icon">
                <ShieldCheck aria-hidden="true" size={20} />
              </span>
              <span className="dashboard-stat-label">Tracked applications</span>
              <strong>
                {summaryState === "success"
                  ? (dashboardSummary?.application_total ?? 0)
                  : "—"}
              </strong>
              <span className="dashboard-stat-footnote">
                User-reported progress
              </span>
            </article>
          </section>

          <aside
            aria-label="Catalogue data notice"
            className="dashboard-data-note"
          >
            <ShieldCheck aria-hidden="true" size={18} />
            <p>
              <strong>Check the source before acting.</strong> Scheme records
              may need review; eligibility assessments are preliminary and
              never guarantee approval.
            </p>
            <a
              href="https://www.india.gov.in/"
              rel="noreferrer"
              target="_blank"
            >
              National Portal of India
              <ArrowRight aria-hidden="true" size={14} />
            </a>
          </aside>

          <section
            aria-labelledby="dashboard-recommendations-title"
            className="dashboard-section"
            id="recommendations"
          >
            <div className="dashboard-section-heading">
              <div>
                <p className="eyebrow">Transparent profile matching</p>
                <h2 id="dashboard-recommendations-title">
                  Recommended for you
                </h2>
                <p>
                  Matches use recorded audience labels and verified structured
                  criteria only.
                </p>
              </div>
              <Link className="dashboard-view-all" to="/schemes">
                Explore all schemes
                <ArrowRight aria-hidden="true" size={16} />
              </Link>
            </div>
            {recommendationPage && !recommendationPage.profile_complete && (
              <aside className="dashboard-profile-prompt">
                <UserRound aria-hidden="true" size={18} />
                <p>
                  Complete your profile to improve discovery. Still needed:{" "}
                  {recommendationPage.missing_profile_fields.join(", ")}.
                </p>
                <Link to="/profile">Complete profile</Link>
              </aside>
            )}
            {recommendationState === "loading" && (
              <div aria-label="Loading scheme records" className="scheme-grid">
                {Array.from({ length: 3 }, (_, index) => (
                  <div
                    aria-hidden="true"
                    className="scheme-skeleton"
                    key={index}
                  />
                ))}
              </div>
            )}
            {recommendationState === "error" && (
              <div className="dashboard-load-error" role="alert">
                <p>{recommendationError}</p>
                <button
                  className="dashboard-retry-button"
                  onClick={() => setReloadKey((current) => current + 1)}
                  type="button"
                >
                  Try again
                </button>
              </div>
            )}
            {recommendationState === "success" &&
              (recommendationPage?.items.length ? (
                <div className="recommendation-grid">
                  {recommendationPage.items.map((recommendation) => (
                    <RecommendationCard
                      key={recommendation.scheme_id}
                      recommendation={recommendation}
                    />
                  ))}
                </div>
              ) : (
                <div className="dashboard-empty-state">
                  <Search aria-hidden="true" size={22} />
                  <div>
                    <p>No relevant scheme records could be matched yet.</p>
                    <span>
                      Add a beneficiary group to your profile or browse all
                      records. Unverified schemes are not treated as confirmed
                      recommendations.
                    </span>
                  </div>
                  <Link to="/profile">Review profile</Link>
                </div>
              ))}
          </section>

          <section
            aria-labelledby="dashboard-jobs-title"
            className="dashboard-section"
            id="job-recommendations"
          >
            <div className="dashboard-section-heading">
              <div>
                <p className="eyebrow">Official recruitment notices</p>
                <h2 id="dashboard-jobs-title">
                  Government job recommendations
                </h2>
                <p>
                  Matches use optional job preferences in your profile.
                  Reservation category is not collected.
                </p>
              </div>
              <Link className="dashboard-view-all" to="/jobs">
                Browse all jobs
                <ArrowRight aria-hidden="true" size={16} />
              </Link>
            </div>
            {jobRecommendationState === "loading" && (
              <p aria-live="polite" className="jobs-loading">
                Loading recently reviewed job matches…
              </p>
            )}
            {jobRecommendationState === "error" && (
              <div className="dashboard-load-error" role="alert">
                <p>{jobRecommendationError}</p>
                <button
                  className="dashboard-retry-button"
                  onClick={() => setReloadKey((current) => current + 1)}
                  type="button"
                >
                  Try again
                </button>
              </div>
            )}
            {jobRecommendationState === "success" &&
              (jobRecommendations.length ? (
                <div className="government-job-grid">
                  {jobRecommendations.slice(0, 3).map((recommendation) => (
                    <GovernmentJobCard
                      job={recommendation}
                      key={recommendation.slug}
                      showMatch
                    />
                  ))}
                </div>
              ) : (
                <div className="dashboard-empty-state">
                  <BriefcaseBusiness aria-hidden="true" size={22} />
                  <p>No recently reviewed vacancies match your profile yet.</p>
                  <Link to="/profile">Review job preferences</Link>
                </div>
              ))}
          </section>

          <section
            aria-labelledby="dashboard-deadlines-title"
            className="dashboard-section"
          >
            <div className="dashboard-section-heading">
              <div>
                <p className="eyebrow">Only source-backed dates</p>
                <h2 id="dashboard-deadlines-title">
                  Verified upcoming deadlines
                </h2>
              </div>
            </div>
            {summaryState === "error" && (
              <p className="inline-error" role="alert">
                {summaryError}
              </p>
            )}
            {summaryState === "success" &&
              (dashboardSummary?.verified_upcoming_deadlines.length ? (
                <ul className="dashboard-deadline-list">
                  {dashboardSummary.verified_upcoming_deadlines.map(
                    (deadline) => (
                      <li key={`${deadline.scheme_id}-${deadline.closes_at}`}>
                        <div>
                          <Link to={`/schemes/${deadline.scheme_id}`}>
                            {deadline.scheme_name}
                          </Link>
                          <span>
                            Closes{" "}
                            {new Intl.DateTimeFormat(undefined, {
                              dateStyle: "medium",
                            }).format(new Date(deadline.closes_at))}
                          </span>
                        </div>
                        <a
                          href={deadline.source_url}
                          rel="noreferrer"
                          target="_blank"
                        >
                          {deadline.source_title ?? "Verified source"}
                        </a>
                      </li>
                    ),
                  )}
                </ul>
              ) : (
                <div className="dashboard-empty-state">
                  <ShieldCheck aria-hidden="true" size={20} />
                  <p>No verified upcoming deadlines are available.</p>
                </div>
              ))}
          </section>

          <section
            aria-labelledby="dashboard-applications-title"
            className="dashboard-section"
          >
            <div className="dashboard-section-heading">
              <div>
                <p className="eyebrow">Your own progress</p>
                <h2 id="dashboard-applications-title">Application tracking</h2>
              </div>
            </div>
            {summaryState === "success" &&
              (dashboardSummary?.application_total ? (
                <ul className="dashboard-application-summary">
                  {Object.entries(
                    dashboardSummary.application_status_counts,
                  ).map(([status, count]) => (
                    <li key={status}>
                      <span>{status.replaceAll("_", " ")}</span>
                      <strong>{count}</strong>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="dashboard-empty-state">
                  <FileSearch aria-hidden="true" size={20} />
                  <p>You are not tracking any scheme applications yet.</p>
                  <Link to="/schemes">Explore schemes</Link>
                </div>
              ))}
          </section>

          <section
            aria-labelledby="saved-schemes-title"
            className="dashboard-section dashboard-saved-section"
            id="saved-schemes"
          >
            <div className="dashboard-section-heading">
              <div>
                <p className="eyebrow">Your shortlist</p>
                <h2 id="saved-schemes-title">Saved schemes</h2>
                <p>Records you have saved in this browser.</p>
              </div>
            </div>
            {storageError && (
              <p className="inline-error" role="alert">
                {storageError}
              </p>
            )}
            {loadState === "error" && (
              <div className="dashboard-load-error" role="alert">
                <p>{loadError}</p>
                <button
                  className="dashboard-retry-button"
                  onClick={() => setReloadKey((current) => current + 1)}
                  type="button"
                >
                  Try again
                </button>
              </div>
            )}
            {loadState === "success" &&
              (savedSchemes.length > 0 ? (
                <div className="scheme-grid dashboard-scheme-grid">
                  {savedSchemes.slice(0, 3).map((scheme) => (
                    <SchemeCard key={scheme.id} scheme={scheme} />
                  ))}
                </div>
              ) : (
                <div className="dashboard-empty-state">
                  <Bookmark aria-hidden="true" size={22} />
                  <p>Your saved records will appear here.</p>
                  <Link to="/schemes">Browse the catalogue</Link>
                </div>
              ))}
          </section>
        </div>
      </section>
    </div>
  );
}
