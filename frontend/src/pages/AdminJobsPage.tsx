import { AlertTriangle, Check, Plus, RefreshCw, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { useAuth } from "../context/AuthContext";
import { adminService } from "../lib/admin";
import type { AdminJobInput } from "../lib/admin";
import type { GovernmentJob } from "../lib/jobs";

const educationLevels = [
  "No formal schooling",
  "Primary",
  "Secondary",
  "Higher secondary",
  "Diploma or vocational",
  "Undergraduate",
  "Postgraduate",
  "Other",
] as const;

function lines(value: FormDataEntryValue | null) {
  return String(value ?? "")
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function optionalNumber(value: FormDataEntryValue | null) {
  const text = String(value ?? "").trim();
  return text ? Number(text) : null;
}

function educationLevel(value: string): AdminJobInput["minimum_education_level"] {
  return educationLevels.find((level) => level === value) ?? null;
}

function jobStatus(value: string): AdminJobInput["status"] {
  switch (value) {
    case "open":
    case "upcoming":
    case "closed":
      return value;
    default:
      return "unknown";
  }
}

function dateTime(value: FormDataEntryValue | null) {
  const text = String(value ?? "").trim();
  return text ? `${text}:00+05:30` : null;
}

function dateTimeInput(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const parts = new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    hour: "2-digit",
    hourCycle: "h23",
    minute: "2-digit",
    month: "2-digit",
    timeZone: "Asia/Kolkata",
    year: "numeric",
  }).formatToParts(date);
  const get = (type: string) =>
    parts.find((part) => part.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}

function documentLines(job: GovernmentJob) {
  return job.documents
    .map(
      (document) =>
        `${document.name}${document.description ? ` | ${document.description}` : ""}${document.is_required ? "" : " | optional"}`,
    )
    .join("\n");
}

function inputFromForm(form: HTMLFormElement): AdminJobInput {
  const data = new FormData(form);
  const deadline = dateTime(data.get("application_deadline"));
  const documents = lines(data.get("documents")).map((line) => {
    const [name = "", description = "", requirement = ""] = line
      .split("|")
      .map((part) => part.trim());
    return {
      name,
      description: description || null,
      is_required: requirement.toLowerCase() !== "optional",
    };
  });
  return {
    slug: String(data.get("slug") ?? "").trim(),
    title: String(data.get("title") ?? "").trim(),
    recruiting_body: String(data.get("recruiting_body") ?? "").trim(),
    description: String(data.get("description") ?? "").trim(),
    employment_type: String(data.get("employment_type") ?? "").trim() || null,
    eligible_states: lines(data.get("eligible_states")),
    minimum_qualification:
      String(data.get("minimum_qualification") ?? "").trim() || null,
    minimum_education_level: educationLevel(
      String(data.get("minimum_education_level") ?? "").trim(),
    ),
    field_of_study: String(data.get("field_of_study") ?? "").trim() || null,
    minimum_experience_years: optionalNumber(
      data.get("minimum_experience_years"),
    ),
    minimum_age: optionalNumber(data.get("minimum_age")),
    maximum_age: optionalNumber(data.get("maximum_age")),
    keywords: lines(data.get("keywords")),
    application_opens: dateTime(data.get("application_opens")),
    application_deadline: deadline,
    deadline_status: deadline ? "known" : "unknown",
    official_notice_url: String(data.get("official_notice_url") ?? "").trim(),
    application_url: String(data.get("application_url") ?? "").trim() || null,
    status: jobStatus(String(data.get("status") ?? "unknown")),
    documents,
    reason: String(data.get("reason") ?? "").trim(),
  };
}

function JobForm({
  job,
  busy,
  onSubmit,
}: {
  job?: GovernmentJob;
  busy: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="admin-job-form" onSubmit={onSubmit}>
      <div className="admin-job-form__grid">
        <label>
          Job title
          <input defaultValue={job?.title ?? ""} maxLength={200} name="title" required />
        </label>
        <label>
          Recruiting body
          <input
            defaultValue={job?.recruiting_body ?? ""}
            maxLength={200}
            name="recruiting_body"
            required
          />
        </label>
        <label>
          URL slug
          <input
            defaultValue={job?.slug ?? ""}
            maxLength={220}
            name="slug"
            pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
            readOnly={Boolean(job)}
            required
          />
        </label>
        <label>
          Employment type
          <input
            defaultValue={job?.employment_type ?? ""}
            maxLength={80}
            name="employment_type"
          />
        </label>
        <label className="admin-job-form__wide">
          Vacancy description
          <textarea
            defaultValue={job?.description ?? ""}
            minLength={10}
            name="description"
            required
            rows={4}
          />
        </label>
        <label>
          Minimum education level
          <select
            defaultValue={job?.minimum_education_level ?? ""}
            name="minimum_education_level"
          >
            <option value="">Not stated</option>
            {educationLevels.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </label>
        <label>
          Specific qualification
          <input
            defaultValue={job?.minimum_qualification ?? ""}
            maxLength={200}
            name="minimum_qualification"
          />
        </label>
        <label>
          Field of study
          <input
            defaultValue={job?.field_of_study ?? ""}
            maxLength={120}
            name="field_of_study"
          />
        </label>
        <label>
          Minimum experience (years)
          <input
            defaultValue={job?.minimum_experience_years ?? ""}
            max="60"
            min="0"
            name="minimum_experience_years"
            type="number"
          />
        </label>
        <label>
          Minimum age
          <input
            defaultValue={job?.minimum_age ?? ""}
            max="100"
            min="18"
            name="minimum_age"
            type="number"
          />
        </label>
        <label>
          Maximum age
          <input
            defaultValue={job?.maximum_age ?? ""}
            max="100"
            min="18"
            name="maximum_age"
            type="number"
          />
        </label>
        <label>
          Application status
          <select defaultValue={job?.status ?? "unknown"} name="status">
            <option value="unknown">Unknown / needs review</option>
            <option value="upcoming">Upcoming</option>
            <option value="open">Applications open</option>
            <option value="closed">Closed</option>
          </select>
        </label>
        <label>
          Application opens (India time)
          <input
            defaultValue={dateTimeInput(job?.application_opens ?? null)}
            name="application_opens"
            type="datetime-local"
          />
        </label>
        <label>
          Application deadline (India time)
          <input
            defaultValue={dateTimeInput(job?.application_deadline ?? null)}
            name="application_deadline"
            type="datetime-local"
          />
        </label>
        <label className="admin-job-form__wide">
          Eligible states or union territories (one per line; leave blank if
          nationwide)
          <textarea
            defaultValue={job?.eligible_states.join("\n") ?? ""}
            name="eligible_states"
            rows={3}
          />
        </label>
        <label className="admin-job-form__wide">
          Keywords (one per line)
          <textarea
            defaultValue={job?.keywords.join("\n") ?? ""}
            name="keywords"
            rows={3}
          />
        </label>
        <label className="admin-job-form__wide">
          Required documents (one per line: name | details | optional)
          <textarea
            defaultValue={job ? documentLines(job) : ""}
            name="documents"
            rows={4}
          />
        </label>
        <label className="admin-job-form__wide">
          Official notice URL (HTTPS)
          <input
            defaultValue={job?.official_notice_url ?? ""}
            name="official_notice_url"
            required
            type="url"
          />
        </label>
        <label className="admin-job-form__wide">
          Application URL (optional, HTTPS)
          <input
            defaultValue={job?.application_url ?? ""}
            name="application_url"
            type="url"
          />
        </label>
        <label className="admin-job-form__wide">
          Source review note
          <textarea
            minLength={10}
            name="reason"
            required
            rows={3}
          />
        </label>
      </div>
      <button className="button button--primary" disabled={busy} type="submit">
        {job ? <Check aria-hidden="true" size={16} /> : <Plus aria-hidden="true" size={16} />}
        {busy ? "Saving…" : job ? "Save changes" : "Add notice for review"}
      </button>
    </form>
  );
}

export function AdminJobsPage() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState<GovernmentJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setJobs(await adminService.listJobs());
      setError(null);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Administrator job notices could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user?.is_admin) void load();
  }, [load, user?.is_admin]);

  async function saveJob(
    event: FormEvent<HTMLFormElement>,
    slug?: string,
  ) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = inputFromForm(form);
    const key = slug ?? "new";
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      if (slug) {
        await adminService.updateJob(slug, input);
        setNotice("Changes saved. The notice must be reviewed again before publication.");
      } else {
        await adminService.createJob(input);
        form.reset();
        setNotice("Notice added as unverified. Review it against the official source before verification.");
      }
      await load();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "The job notice could not be saved.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function verifyJob(job: GovernmentJob) {
    const reviewNote = window.prompt(
      `Review ${job.title} against its official notice and enter a note:`,
    );
    if (!reviewNote || reviewNote.trim().length < 10) return;
    setBusy(job.slug);
    setError(null);
    setNotice(null);
    try {
      await adminService.verifyJob(job.slug, reviewNote.trim());
      setNotice("Job notice verified and published for discovery.");
      await load();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "The job notice could not be verified.",
      );
    } finally {
      setBusy(null);
    }
  }

  if (!user?.is_admin) {
    return (
      <section className="admin-page">
        <div className="admin-state" role="alert">
          <AlertTriangle aria-hidden="true" size={20} />
          <p>Administrator access is required to manage recruitment notices.</p>
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="admin-jobs-title" className="admin-jobs-page">
      <header className="admin-header">
        <div>
          <p className="eyebrow">Central recruitment notices</p>
          <h1 id="admin-jobs-title">Government job administration</h1>
          <p>
            Add details from official notices. New and edited notices remain
            unpublished until an administrator verifies the source and dates.
          </p>
        </div>
        <button
          className="button button--secondary"
          disabled={loading || busy !== null}
          onClick={() => void load()}
          type="button"
        >
          <RefreshCw aria-hidden="true" size={16} />
          Refresh
        </button>
      </header>

      {error && <p className="admin-job-error" role="alert">{error}</p>}
      {notice && <p className="admin-success" role="status">{notice}</p>}

      <section aria-labelledby="create-job-title" className="admin-job-panel">
        <h2 id="create-job-title">Add a recruitment notice</h2>
        <p>
          Dates, qualifications, and document requirements should match the
          linked original notice. Do not enter assumptions as facts.
        </p>
        <JobForm
          busy={busy === "new"}
          onSubmit={(event) => void saveJob(event)}
        />
      </section>

      <section aria-labelledby="review-jobs-title" className="admin-job-panel">
        <h2 id="review-jobs-title">Curated notices</h2>
        {loading ? (
          <p aria-live="polite">Loading notices…</p>
        ) : jobs.length ? (
          <div className="admin-job-list">
            {jobs.map((job) => (
              <details className="admin-job-item" key={job.slug}>
                <summary>
                  <span>
                    <strong>{job.title}</strong>
                    <small>
                      {job.recruiting_body} · {job.verification_status}
                    </small>
                  </span>
                  <span className="admin-job-item__status">
                    {job.status.replaceAll("_", " ")}
                  </span>
                </summary>
                <div className="admin-job-item__body">
                  <a
                    href={job.official_notice_url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    Open official notice
                  </a>
                  <JobForm
                    busy={busy === job.slug}
                    job={job}
                    onSubmit={(event) => void saveJob(event, job.slug)}
                  />
                  {job.status === "open" || job.status === "upcoming" ? (
                    <button
                      className="button button--secondary"
                      disabled={busy !== null}
                      onClick={() => void verifyJob(job)}
                      type="button"
                    >
                      <ShieldCheck aria-hidden="true" size={16} />
                      Verify and publish
                    </button>
                  ) : (
                    <p className="admin-job-review-note">
                      Set the notice to Open or Upcoming after checking the
                      official dates before verification.
                    </p>
                  )}
                </div>
              </details>
            ))}
          </div>
        ) : (
          <p>No central recruitment notices have been entered yet.</p>
        )}
      </section>
    </section>
  );
}
