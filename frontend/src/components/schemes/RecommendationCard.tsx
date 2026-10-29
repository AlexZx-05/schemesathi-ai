import { ArrowRight, Bookmark, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";

import { useSavedSchemes } from "../../context/SavedSchemesContext";
import type { SchemeRecommendation } from "../../lib/schemes/service";

const outcomeLabels: Record<SchemeRecommendation["eligibility_status"], string> = {
  potentially_eligible: "Potentially eligible",
  more_information_required: "More information required",
  known_criteria_not_satisfied: "Known criteria not satisfied",
  unable_to_determine: "Unable to determine",
};

export function RecommendationCard({
  recommendation,
}: {
  recommendation: SchemeRecommendation;
}) {
  const { savedSchemeIds, toggleSavedScheme } = useSavedSchemes();
  const isSaved = savedSchemeIds.includes(recommendation.scheme_id);

  return (
    <article
      aria-labelledby={`recommendation-${recommendation.scheme_id}`}
      className="recommendation-card"
    >
      <div className="recommendation-card-topline">
        <span className="scheme-category">
          {recommendation.category ?? "Scheme"}
        </span>
        <span className="verification-badge">Verified source</span>
      </div>
      <div className="recommendation-card-heading">
        <h3 id={`recommendation-${recommendation.scheme_id}`}>
          {recommendation.scheme_name}
        </h3>
        <span
          className={`eligibility-outcome eligibility-outcome--${recommendation.eligibility_status}`}
        >
          {outcomeLabels[recommendation.eligibility_status]}
        </span>
      </div>
      <p className="recommendation-summary">{recommendation.summary}</p>

      {recommendation.reasons.length > 0 && (
        <section aria-label="Why this was recommended">
          <h4>Why it appears here</h4>
          <ul className="recommendation-reasons">
            {recommendation.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </section>
      )}

      {recommendation.criteria.length > 0 && (
        <section aria-label="Eligibility criteria comparison">
          <h4>Recorded criteria</h4>
          <ul className="recommendation-criteria">
            {recommendation.criteria.map((criterion) => (
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
        </section>
      )}

      {recommendation.missing_information.length > 0 && (
        <section aria-label="Information needed">
          <h4>Information to confirm</h4>
          <p>{recommendation.missing_information.join(", ")}</p>
        </section>
      )}

      <div className="recommendation-sources">
        <strong>Official sources</strong>
        {recommendation.sources.length > 0 ? (
          recommendation.sources.map((source) => (
            <a
              href={source.url}
              key={source.url}
              rel="noreferrer"
              target="_blank"
            >
              {source.title ?? "Verified source"}
              <ExternalLink aria-hidden="true" size={13} />
            </a>
          ))
        ) : (
          <span>No verified source is available for this record.</span>
        )}
      </div>

      <div className="recommendation-card-actions">
        <Link
          className="button button--primary"
          to={`/schemes/${recommendation.scheme_id}`}
        >
          Review details
          <ArrowRight aria-hidden="true" size={15} />
        </Link>
        <button
          aria-label={`${isSaved ? "Remove saved" : "Save"} ${recommendation.scheme_name}`}
          aria-pressed={isSaved}
          className="save-scheme-button"
          onClick={() => toggleSavedScheme(recommendation.scheme_id)}
          type="button"
        >
          <Bookmark
            aria-hidden="true"
            fill={isSaved ? "currentColor" : "none"}
            size={16}
          />
          <span>{isSaved ? "Saved" : "Save"}</span>
        </button>
      </div>
    </article>
  );
}
