import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  Bookmark,
  CalendarDays,
  CheckCircle2,
  FileText,
  Info,
  LoaderCircle,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useSavedSchemes } from "../context/SavedSchemesContext";
import { schemeService } from "../lib/schemes/service";
import type { EligibilityAssessment } from "../lib/schemes/service";
import type { Scheme } from "../lib/schemes/types";

type DetailState = "loading" | "success" | "not-found" | "error";

export function SchemeDetailsPage() {
  const { schemeId } = useParams();
  const [scheme, setScheme] = useState<Scheme | null>(null);
  const [state, setState] = useState<DetailState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [eligibility, setEligibility] = useState<EligibilityAssessment | null>(
    null,
  );
  const [eligibilityLoading, setEligibilityLoading] = useState(false);
  const [eligibilityError, setEligibilityError] = useState<string | null>(null);
  const { status: authStatus } = useAuth();
  const { savedSchemeIds, storageError, toggleSavedScheme } = useSavedSchemes();

  useEffect(() => {
    const controller = new AbortController();
    setState("loading");
    setError(null);

    if (!schemeId) {
      setScheme(null);
      setState("not-found");
      return () => controller.abort();
    }

    schemeService
      .getSchemeById(schemeId)
      .then((loadedScheme) => {
        if (controller.signal.aborted) {
          return;
        }
        setScheme(loadedScheme);
        setState(loadedScheme ? "success" : "not-found");
      })
      .catch((loadError: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "The scheme record could not be loaded.",
          );
          setState("error");
        }
      });

    return () => controller.abort();
  }, [schemeId]);

  if (state === "loading") {
    return (
      <section aria-live="polite" className="discovery-page">
        <div className="detail-loading">Loading scheme information…</div>
      </section>
    );
  }

  if (state === "not-found") {
    return (
      <section
        aria-labelledby="detail-missing-title"
        className="discovery-page"
      >
        <Link className="back-link" to="/schemes">
          <ArrowLeft aria-hidden="true" size={17} />
          Back to schemes
        </Link>
        <div className="discovery-state">
          <span aria-hidden="true" className="empty-state-icon">
            !
          </span>
          <h1 id="detail-missing-title">Scheme record not found</h1>
          <p>
            This scheme may have been removed or the link may be incorrect.
          </p>
          <Link className="button button--primary" to="/schemes">
            Browse schemes
          </Link>
        </div>
      </section>
    );
  }

  if (state === "error" || !scheme) {
    return (
      <section aria-labelledby="detail-error-title" className="discovery-page">
        <Link className="back-link" to="/schemes">
          <ArrowLeft aria-hidden="true" size={17} />
          Back to schemes
        </Link>
        <div className="discovery-state discovery-state--error" role="alert">
          <h1 id="detail-error-title">Unable to load this record</h1>
          <p>{error ?? "The scheme record could not be loaded."}</p>
        </div>
      </section>
    );
  }

  const isSaved = savedSchemeIds.includes(scheme.id);

  async function checkEligibility(schemeId: string) {
    setEligibilityError(null);
    setEligibilityLoading(true);
    try {
      const result = await schemeService.assessEligibility(schemeId);
      setEligibility(result);
    } catch (requestError) {
      setEligibilityError(
          requestError instanceof Error
            ? requestError.message
            : "The preliminary assessment could not be completed.",
      );
    } finally {
      setEligibilityLoading(false);
    }
  }

  return (
    <article className="discovery-page scheme-details-page">
      <Link className="back-link" to="/schemes">
        <ArrowLeft aria-hidden="true" size={17} />
        Back to schemes
      </Link>

      <header className="scheme-detail-header">
        <div className="scheme-card-topline">
          <span className="scheme-category">
            {scheme.category ?? "Uncategorized"}
          </span>
          <span className="verification-badge">Verified source</span>
        </div>
        <h1 className="page-title">{scheme.name}</h1>
        <p className="page-intro">{scheme.shortDescription}</p>
        <div className="detail-meta">
          <span>
            <strong>Audience:</strong>{" "}
            {scheme.beneficiaries.join(", ") || "Not recorded"}
          </span>
          <span>
            <strong>Government level:</strong> {scheme.governmentLevel}
          </span>
          <span>
            <CalendarDays aria-hidden="true" size={16} />
            <strong>Last verified:</strong>{" "}
            {scheme.lastVerifiedDate ?? "Not verified"}
          </span>
        </div>
        <button
          aria-pressed={isSaved}
          className="button button--secondary detail-save-button"
          onClick={() => toggleSavedScheme(scheme.id)}
          type="button"
        >
          <Bookmark
            aria-hidden="true"
            fill={isSaved ? "currentColor" : "none"}
            size={17}
          />
          {isSaved ? "Saved" : "Save scheme"}
        </button>
        {authStatus === "authenticated" ? (
          <>
            <button
              className="button button--primary detail-eligibility-button"
              disabled={eligibilityLoading}
              onClick={() => void checkEligibility(scheme.id)}
              type="button"
            >
              {eligibilityLoading ? (
                <>
                  <LoaderCircle aria-hidden="true" className="spin" size={17} />
                  Checking…
                </>
              ) : (
                <>
                  <CheckCircle2 aria-hidden="true" size={17} />
                  Check preliminary eligibility
                </>
              )}
            </button>
            <Link
              className="button button--secondary detail-eligibility-button"
              to={`/schemes/${scheme.id}/eligibility-check`}
            >
              Open guided assessment
            </Link>
            <Link
              className="button button--secondary detail-eligibility-button"
              to={`/schemes/${scheme.id}/documents`}
            >
              Prepare documents
            </Link>
            <Link
              className="button button--secondary detail-eligibility-button"
              to={`/schemes/${scheme.id}/apply`}
            >
              Application guidance
            </Link>
          </>
        ) : (
          <Link
            className="button button--secondary detail-eligibility-button"
            to="/login"
          >
            Sign in to check criteria
          </Link>
        )}
      </header>

      {storageError && (
        <p className="inline-error" role="alert">
          {storageError}
        </p>
      )}

      <aside
        aria-label="Verification status"
        className="source-review-notice"
      >
        <Info aria-hidden="true" size={19} />
        <p>
          <strong>Reviewed against an official source.</strong> Review the
          linked source and verification date before acting; scheme details may
          change.
        </p>
      </aside>

      {eligibilityError && (
        <p className="inline-error" role="alert">
          {eligibilityError}
        </p>
      )}
      {eligibility && (
        <section
          aria-labelledby="eligibility-assessment-title"
          className="eligibility-assessment"
          id="eligibility-assessment"
        >
          <header>
            <div>
              <p className="eyebrow">Profile-based criteria review</p>
              <h2 id="eligibility-assessment-title">
                Preliminary eligibility assessment
              </h2>
              <p>{eligibility.summary}</p>
            </div>
            <span
              className={`eligibility-outcome eligibility-outcome--${eligibility.outcome}`}
            >
              {eligibility.outcome.replaceAll("_", " ")}
            </span>
          </header>
          {eligibility.criteria.length > 0 ? (
            <ul className="eligibility-criteria-list">
              {eligibility.criteria.map((criterion) => (
                <li key={criterion.rule_id}>
                  <span>
                    <strong>{criterion.criterion}</strong>
                    <span>{criterion.explanation}</span>
                  </span>
                  <span
                    className={`eligibility-criterion-status eligibility-criterion-status--${criterion.result}`}
                  >
                    {criterion.result.replaceAll("_", " ")}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p>No structured criteria are currently available to assess.</p>
          )}
          {eligibility.sources.length > 0 && (
            <div className="eligibility-sources">
              <strong>Verified sources</strong>
              {eligibility.sources.map((source) => (
                <a
                  href={source.url}
                  key={source.url}
                  rel="noreferrer"
                  target="_blank"
                >
                  {source.title ?? source.url}
                </a>
              ))}
            </div>
          )}
          <p className="eligibility-disclaimer">{eligibility.disclaimer}</p>
        </section>
      )}

      <div className="scheme-detail-grid">
        <div className="scheme-detail-main">
          <section aria-labelledby="overview-title" className="detail-section">
            <h2 id="overview-title">Overview</h2>
            <p>{scheme.shortDescription}</p>
          </section>
          <section aria-labelledby="benefits-title" className="detail-section">
            <h2 id="benefits-title">Benefits</h2>
            {scheme.benefits.length ? (
              <ul>
                {scheme.benefits.map((benefit) => (
                  <li key={benefit}>{benefit}</li>
                ))}
              </ul>
            ) : (
              <p>No reviewed benefit information is recorded yet.</p>
            )}
          </section>
          <section
            aria-labelledby="eligibility-title"
            className="detail-section"
            id="eligibility"
          >
            <h2 id="eligibility-title">
              <CheckCircle2 aria-hidden="true" size={20} />
              Eligibility criteria
            </h2>
            {scheme.eligibilityCriteria.length ? (
              <ul>
                {scheme.eligibilityCriteria.map((criterion) => (
                  <li key={criterion}>{criterion}</li>
                ))}
              </ul>
            ) : (
              <p>No reviewed eligibility information is recorded yet.</p>
            )}
            <p className="detail-inline-note">
              These listed criteria are descriptive. The guided assessment
              checks only criteria supported by reviewed structured rules.
            </p>
          </section>
          <section aria-labelledby="documents-title" className="detail-section">
            <h2 id="documents-title">
              <FileText aria-hidden="true" size={20} />
              Required documents
            </h2>
            {scheme.requiredDocuments.length ? (
              <ul>
                {scheme.requiredDocuments.map((document) => (
                  <li key={document}>{document}</li>
                ))}
              </ul>
            ) : (
              <p>No reviewed document requirements are recorded yet.</p>
            )}
          </section>
          <section aria-labelledby="procedure-title" className="detail-section">
            <h2 id="procedure-title">Application procedure</h2>
            {scheme.applicationProcedure.length ? (
              <ol>
                {scheme.applicationProcedure.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            ) : (
              <p>No reviewed application steps are recorded yet.</p>
            )}
          </section>
        </div>

        <aside className="official-source-panel">
          <h2>Source links</h2>
          {scheme.sources?.length ? (
            <ul className="official-source-list">
              {scheme.sources.map((source) => (
                <li key={source.url}>
                  <a
                    className="official-source-link"
                    href={source.url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {source.title ?? source.url}
                    <ArrowUpRight aria-hidden="true" size={16} />
                  </a>
                  <span>
                    {source.status === "verified"
                      ? "Verified source"
                      : source.status === "stale"
                        ? "Source needs re-verification"
                        : source.status === "unavailable"
                          ? "Source unavailable"
                          : "Source not yet verified"}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p>
              {scheme.officialSource
                ? "No source links are recorded for this entry."
                : "No source link is recorded. Check the relevant government department or portal."}
            </p>
          )}
          {scheme.officialSource && !scheme.sources?.some(
            (source) =>
              source.url === scheme.officialSource && source.status === "verified",
          ) && (
            <a
              className="official-source-link"
              href={scheme.officialSource}
              rel="noreferrer"
              target="_blank"
            >
              Open verified official source
              <ArrowUpRight aria-hidden="true" size={16} />
            </a>
          )}
        </aside>
      </div>
    </article>
  );
}
