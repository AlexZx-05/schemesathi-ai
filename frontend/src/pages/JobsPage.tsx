import { ArrowRight, BriefcaseBusiness, Search } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { GovernmentJobCard } from "../components/jobs/GovernmentJobCard";
import { useAuth } from "../context/AuthContext";
import {
  jobService,
  type GovernmentJob,
  type JobRecommendation,
} from "../lib/jobs";

type LoadState = "loading" | "success" | "error";

export function JobsPage() {
  const { status } = useAuth();
  const [jobs, setJobs] = useState<GovernmentJob[]>([]);
  const [recommendations, setRecommendations] = useState<JobRecommendation[]>(
    [],
  );
  const [profileComplete, setProfileComplete] = useState(false);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [recommendationState, setRecommendationState] =
    useState<LoadState | "idle">("idle");
  const [error, setError] = useState<string | null>(null);
  const [recommendationError, setRecommendationError] = useState<
    string | null
  >(null);
  const [queryInput, setQueryInput] = useState("");
  const [query, setQuery] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setLoadState("loading");
    setError(null);
    jobService
      .listJobs(query)
      .then((result) => {
        if (!active) return;
        setJobs(result.items);
        setLoadState("success");
      })
      .catch((cause: unknown) => {
        if (!active) return;
        setError(
          cause instanceof Error
            ? cause.message
            : "Government job notices could not be loaded.",
        );
        setLoadState("error");
      });
    return () => {
      active = false;
    };
  }, [query, reloadKey]);

  useEffect(() => {
    if (status !== "authenticated") {
      setRecommendationState("idle");
      return;
    }
    let active = true;
    setRecommendationState("loading");
    setRecommendationError(null);
    jobService
      .getRecommendations()
      .then((result) => {
        if (!active) return;
        setRecommendations(result.items);
        setProfileComplete(result.profile_complete);
        setRecommendationState("success");
      })
      .catch((cause: unknown) => {
        if (!active) return;
        setRecommendationError(
          cause instanceof Error
            ? cause.message
            : "Personalized job matches could not be loaded.",
        );
        setRecommendationState("error");
      });
    return () => {
      active = false;
    };
  }, [status, reloadKey]);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setQuery(queryInput.trim());
  }

  return (
    <section aria-labelledby="jobs-title" className="jobs-page">
      <header className="jobs-page__header">
        <div>
          <p className="eyebrow">Central government opportunities</p>
          <h1 id="jobs-title">Government jobs</h1>
          <p>
            Browse current and upcoming recruitment notices reviewed against
            official sources. Check the original notice before applying.
          </p>
        </div>
        <form className="jobs-search" onSubmit={submitSearch} role="search">
          <label className="visually-hidden" htmlFor="job-search">
            Search government job notices
          </label>
          <Search aria-hidden="true" size={18} />
          <input
            id="job-search"
            onChange={(event) => setQueryInput(event.target.value)}
            placeholder="Search role or recruiting body"
            type="search"
            value={queryInput}
          />
          <button className="button button--primary" type="submit">
            Search
          </button>
        </form>
      </header>

      {status === "authenticated" && (
        <section
          aria-labelledby="job-matches-title"
          className="jobs-section jobs-section--matches"
        >
          <div className="jobs-section__heading">
            <div>
              <p className="eyebrow">Your profile-based matches</p>
              <h2 id="job-matches-title">Recommended for you</h2>
            </div>
            <Link className="button button--secondary" to="/profile">
              Update job preferences
              <ArrowRight aria-hidden="true" size={16} />
            </Link>
          </div>
          {!profileComplete && (
            <p className="jobs-profile-note">
              Add your education, qualification, experience, and preferred
              locations to improve these matches. Job preferences are optional.
            </p>
          )}
          {recommendationState === "loading" && (
            <p aria-live="polite" className="jobs-loading">
              Finding recently reviewed notices that fit your profile…
            </p>
          )}
          {recommendationState === "error" && (
            <div className="jobs-error" role="alert">
              <p>{recommendationError}</p>
              <button
                className="button button--secondary"
                onClick={() => setReloadKey((current) => current + 1)}
                type="button"
              >
                Try again
              </button>
            </div>
          )}
          {recommendationState === "success" &&
            (recommendations.length ? (
              <div className="government-job-grid">
                {recommendations.map((job) => (
                  <GovernmentJobCard
                    job={job}
                    key={job.slug}
                    showMatch
                  />
                ))}
              </div>
            ) : (
              <div className="jobs-empty">
                <BriefcaseBusiness aria-hidden="true" size={22} />
                <p>No reviewed vacancies currently match your profile.</p>
                <span>
                  Try updating your job preferences or browse all current
                  notices below. Matching is guidance, not a decision on
                  eligibility.
                </span>
              </div>
            ))}
        </section>
      )}

      <section aria-labelledby="all-jobs-title" className="jobs-section">
        <div className="jobs-section__heading">
          <div>
            <p className="eyebrow">Recently reviewed notices</p>
            <h2 id="all-jobs-title">Open and upcoming vacancies</h2>
          </div>
        </div>
        {loadState === "loading" && (
          <p aria-live="polite" className="jobs-loading">
            Loading verified government job notices…
          </p>
        )}
        {loadState === "error" && (
          <div className="jobs-error" role="alert">
            <p>{error}</p>
            <button
              className="button button--secondary"
              onClick={() => setReloadKey((current) => current + 1)}
              type="button"
            >
              Try again
            </button>
          </div>
        )}
        {loadState === "success" &&
          (jobs.length ? (
            <div className="government-job-grid">
              {jobs.map((job) => (
                <GovernmentJobCard job={job} key={job.slug} />
              ))}
            </div>
          ) : (
            <div className="jobs-empty">
              <BriefcaseBusiness aria-hidden="true" size={22} />
              <p>No recently reviewed open notices are listed right now.</p>
              <span>
                We do not invent vacancies or deadlines. Check official
                recruitment portals directly and come back for notices that
                have been reviewed here.
              </span>
            </div>
          ))}
      </section>
    </section>
  );
}
