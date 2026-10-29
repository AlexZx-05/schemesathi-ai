import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { GovernmentJobCard } from "../components/jobs/GovernmentJobCard";
import { jobService, type GovernmentJob } from "../lib/jobs";

export function JobDetailsPage() {
  const { jobSlug } = useParams();
  const [job, setJob] = useState<GovernmentJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setJob(null);
    setLoading(true);
    setError(null);
    if (!jobSlug) {
      setError("This job notice could not be found.");
      setLoading(false);
      return;
    }
    jobService
      .getJob(jobSlug)
      .then((result) => {
        if (active) setJob(result);
      })
      .catch((cause: unknown) => {
        if (active) {
          setError(
            cause instanceof Error
              ? cause.message
              : "This government job notice could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [jobSlug]);

  return (
    <section aria-labelledby="job-detail-title" className="jobs-page">
      <Link className="jobs-back-link" to="/jobs">
        Back to government jobs
      </Link>
      {loading && (
        <p aria-live="polite" className="jobs-loading">
          Loading the reviewed notice…
        </p>
      )}
      {error && (
        <div className="jobs-error" role="alert">
          <h1 id="job-detail-title">Notice unavailable</h1>
          <p>{error}</p>
          <Link className="button button--secondary" to="/jobs">
            Browse government jobs
          </Link>
        </div>
      )}
      {job && (
        <>
          <p className="eyebrow">Recently reviewed central recruitment notice</p>
          <h1 className="job-detail-title" id="job-detail-title">
            {job.title}
          </h1>
          <GovernmentJobCard job={job} showDetailsLink={false} />
        </>
      )}
    </section>
  );
}
