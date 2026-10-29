import { ArrowUpRight, BriefcaseBusiness, CalendarClock, FileText } from "lucide-react";
import { Link } from "react-router-dom";

import type { GovernmentJob, JobRecommendation } from "../../lib/jobs";

type Props = {
  job: GovernmentJob | JobRecommendation;
  showMatch?: boolean;
  showDetailsLink?: boolean;
};

function deadlineLabel(job: GovernmentJob) {
  if (job.deadline_status !== "known" || !job.application_deadline) {
    return "Deadline not confirmed — check the official notice";
  }
  const deadline = new Date(job.application_deadline);
  if (Number.isNaN(deadline.getTime())) {
    return "Deadline not confirmed — check the official notice";
  }
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  }).format(deadline);
}

function ageRequirement(job: GovernmentJob) {
  if (job.minimum_age === null && job.maximum_age === null) {
    return "Not listed";
  }
  if (job.minimum_age !== null && job.maximum_age !== null) {
    return `${job.minimum_age}–${job.maximum_age} years`;
  }
  return job.minimum_age !== null
    ? `${job.minimum_age}+ years`
    : `Up to ${job.maximum_age} years`;
}

export function GovernmentJobCard({
  job,
  showMatch = false,
  showDetailsLink = true,
}: Props) {
  const recommendation = "match_reasons" in job ? job : null;

  return (
    <article className="government-job-card">
      <div className="government-job-card__header">
        <span className="government-job-card__icon">
          <BriefcaseBusiness aria-hidden="true" size={20} />
        </span>
        <span className="government-job-card__status">
          {job.status === "upcoming" ? "Upcoming" : "Applications open"}
        </span>
      </div>
      <h3>{job.title}</h3>
      <p className="government-job-card__recruiter">{job.recruiting_body}</p>
      <p className="government-job-card__description">{job.description}</p>

      <dl className="government-job-card__facts">
        <div>
          <dt>
            <CalendarClock aria-hidden="true" size={15} />
            Application deadline
          </dt>
          <dd>{deadlineLabel(job)}</dd>
        </div>
        <div>
          <dt>Qualification</dt>
          <dd>{job.minimum_qualification ?? "See official notice"}</dd>
        </div>
        <div>
          <dt>Education level</dt>
          <dd>{job.minimum_education_level ?? "See official notice"}</dd>
        </div>
        <div>
          <dt>Age limit</dt>
          <dd>{ageRequirement(job)}</dd>
        </div>
        <div>
          <dt>Experience</dt>
          <dd>
            {job.minimum_experience_years === null
              ? "See official notice"
              : `${job.minimum_experience_years}+ years`}
          </dd>
        </div>
        <div>
          <dt>Eligible locations</dt>
          <dd>
            {job.eligible_states.length
              ? job.eligible_states.join(", ")
              : "As stated in the official notice"}
          </dd>
        </div>
      </dl>

      {showMatch && recommendation && (
        <div className="government-job-card__match">
          <strong>Why this may match</strong>
          <ul>
            {recommendation.match_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
          {recommendation.missing_information.length > 0 && (
            <p>
              Confirm before applying:{" "}
              {recommendation.missing_information.join(", ")}.
            </p>
          )}
        </div>
      )}

      <div className="government-job-card__documents">
        <h4>
          <FileText aria-hidden="true" size={16} />
          Documents listed in the notice
        </h4>
        {job.documents.length ? (
          <ul>
            {job.documents.map((document) => (
              <li key={document.id}>
                {document.name}
                {!document.is_required && " (if applicable)"}
                {document.description && <span>{document.description}</span>}
              </li>
            ))}
          </ul>
        ) : (
          <p>
            No document checklist has been confirmed. Review the official
            notice before applying.
          </p>
        )}
      </div>

      <div className="government-job-card__actions">
        {showDetailsLink && (
          <Link className="button button--secondary" to={`/jobs/${job.slug}`}>
            Details
          </Link>
        )}
        {job.application_url && (
          <a
            className="button button--primary"
            href={job.application_url}
            rel="noreferrer"
            target="_blank"
          >
            Apply
            <ArrowUpRight aria-hidden="true" size={16} />
          </a>
        )}
        <a
          className="government-job-card__notice-link"
          href={job.official_notice_url}
          rel="noreferrer"
          target="_blank"
        >
          Official notice
          <ArrowUpRight aria-hidden="true" size={14} />
        </a>
      </div>
      <p className="government-job-card__verification">
        Official notice reviewed{" "}
        {job.last_verified_at
          ? new Intl.DateTimeFormat("en-IN", {
              dateStyle: "medium",
              timeZone: "Asia/Kolkata",
            }).format(new Date(job.last_verified_at))
          : "date unavailable"}
        . Confirm all criteria and dates in the notice.
      </p>
    </article>
  );
}
