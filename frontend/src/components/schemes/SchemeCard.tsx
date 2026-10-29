import { ArrowRight, Bookmark, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";

import { useSavedSchemes } from "../../context/SavedSchemesContext";
import type { Scheme } from "../../lib/schemes/types";

export function SchemeCard({ scheme }: { scheme: Scheme }) {
  const { savedSchemeIds, toggleSavedScheme } = useSavedSchemes();
  const isSaved = savedSchemeIds.includes(scheme.id);

  return (
    <article className="scheme-card">
      <div className="scheme-card-topline">
        <span className="scheme-category">
          {scheme.category ?? "Uncategorized"}
        </span>
        <span className="verification-badge">Verified source</span>
      </div>
      <h2 className="scheme-card-title">
        <Link to={`/schemes/${scheme.id}`}>{scheme.name}</Link>
      </h2>
      <p className="scheme-card-description">{scheme.shortDescription}</p>
      <dl className="scheme-meta">
        <div>
          <dt>For</dt>
          <dd>{scheme.beneficiaries.join(", ") || "Not recorded"}</dd>
        </div>
        <div>
          <dt>Level</dt>
          <dd>
            {scheme.governmentLevel}
          </dd>
        </div>
      </dl>
      <div className="scheme-card-actions">
        <Link
          className="button button--primary scheme-details-link"
          to={`/schemes/${scheme.id}`}
        >
          View details
          <ArrowRight aria-hidden="true" size={16} />
        </Link>
        <Link
          className="button button--secondary scheme-eligibility-link"
          to={`/schemes/${scheme.id}#eligibility`}
        >
          <CheckCircle2 aria-hidden="true" size={16} />
          Eligibility
        </Link>
        <button
          aria-label={`${isSaved ? "Remove saved" : "Save"} ${scheme.name}`}
          aria-pressed={isSaved}
          className="save-scheme-button"
          onClick={() => toggleSavedScheme(scheme.id)}
          type="button"
        >
          <Bookmark
            aria-hidden="true"
            fill={isSaved ? "currentColor" : "none"}
            size={18}
          />
          <span>{isSaved ? "Saved" : "Save"}</span>
        </button>
      </div>
    </article>
  );
}
