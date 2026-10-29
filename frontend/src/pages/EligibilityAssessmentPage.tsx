import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  CircleHelp,
  LoaderCircle,
  ShieldCheck,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { schemeService } from "../lib/schemes/service";
import type {
  EligibilityAssessment,
  EligibilityHypotheticalAnswers,
} from "../lib/schemes/service";
import type { Scheme } from "../lib/schemes/types";

const stateOptions = [
  "Andaman and Nicobar Islands",
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chandigarh",
  "Chhattisgarh",
  "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jammu and Kashmir",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Ladakh",
  "Lakshadweep",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Puducherry",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
];
const educationOptions = [
  "No formal schooling",
  "Primary",
  "Secondary",
  "Higher secondary",
  "Diploma or vocational",
  "Undergraduate",
  "Postgraduate",
  "Other",
];
const incomeOptions = [
  "Prefer not to say",
  "Below ₹1 lakh",
  "₹1–3 lakh",
  "₹3–6 lakh",
  "₹6–10 lakh",
  "Above ₹10 lakh",
];
const occupationOptions = [
  "Student",
  "Farmer",
  "Salaried employee",
  "Self-employed",
  "Job seeker",
  "Homemaker",
  "Other",
];
const employmentOptions = [
  "Employed",
  "Self-employed",
  "Unemployed",
  "Student",
  "Homemaker",
  "Other",
];
const beneficiaryOptions = [
  "Students",
  "Farmers",
  "Job seekers",
  "Women",
  "Children",
  "Families",
  "Low-income households",
  "Persons with disabilities",
  "Senior citizens",
  "Other",
];

type PageState = "loading" | "ready" | "error" | "not-found";
type AnswerValues = Record<string, string | string[]>;

function optionsFor(field: string): string[] | null {
  if (field === "state") return stateOptions;
  if (field === "area_type") return ["Rural", "Urban"];
  if (field === "occupation") return occupationOptions;
  if (field === "employment_status") return employmentOptions;
  if (field === "education_level") return educationOptions;
  if (field === "annual_income_range") return incomeOptions;
  return null;
}

function buildAnswers(values: AnswerValues): EligibilityHypotheticalAnswers {
  const answers: EligibilityHypotheticalAnswers = {};
  for (const [field, value] of Object.entries(values)) {
    if (Array.isArray(value) && field === "beneficiary_categories") {
      answers.beneficiary_categories = value;
      continue;
    }
    if (typeof value !== "string" || !value.trim()) continue;
    switch (field) {
      case "age":
        answers.age = Number(value);
        break;
      case "household_size":
        answers.household_size = Number(value);
        break;
      case "current_student":
        answers.current_student = value === "true";
        break;
      case "district":
        answers.district = value.trim();
        break;
      case "worker_category":
        answers.worker_category = value.trim();
        break;
      case "state":
        answers.state = value;
        break;
      case "area_type":
        if (value === "Rural" || value === "Urban") answers.area_type = value;
        break;
      case "occupation":
        if (occupationOptions.includes(value)) {
          answers.occupation = value as EligibilityHypotheticalAnswers["occupation"];
        }
        break;
      case "employment_status":
        if (employmentOptions.includes(value)) {
          answers.employment_status =
            value as EligibilityHypotheticalAnswers["employment_status"];
        }
        break;
      case "education_level":
        if (educationOptions.includes(value)) {
          answers.education_level =
            value as EligibilityHypotheticalAnswers["education_level"];
        }
        break;
      case "annual_income_range":
        if (incomeOptions.includes(value)) {
          answers.annual_income_range =
            value as EligibilityHypotheticalAnswers["annual_income_range"];
        }
        break;
    }
  }
  return answers;
}

function fieldLabel(field: string): string {
  const labels: Record<string, string> = {
    age: "Age",
    state: "State or union territory",
    district: "District",
    area_type: "Rural or urban area",
    occupation: "Occupation",
    employment_status: "Employment status",
    worker_category: "Worker category",
    education_level: "Highest education level",
    current_student: "Are you currently a student?",
    annual_income_range: "Annual family income range",
    household_size: "Household size",
    beneficiary_categories: "Beneficiary groups",
  };
  return labels[field] ?? field.replaceAll("_", " ");
}

function EligibilityAnswerField({
  field,
  values,
  onChange,
}: {
  field: string;
  values: AnswerValues;
  onChange: (field: string, value: string | string[]) => void;
}) {
  const label = fieldLabel(field);
  if (field === "beneficiary_categories") {
    const selected = Array.isArray(values[field]) ? values[field] : [];
    return (
      <fieldset className="eligibility-answer-field">
        <legend>{label}</legend>
        <div className="eligibility-answer-options">
          {beneficiaryOptions.map((option) => (
            <label key={option}>
              <input
                checked={selected.includes(option)}
                onChange={(event) =>
                  onChange(
                    field,
                    event.target.checked
                      ? [...selected, option]
                      : selected.filter((item) => item !== option),
                  )
                }
                type="checkbox"
              />
              {option}
            </label>
          ))}
        </div>
      </fieldset>
    );
  }

  const options = optionsFor(field);
  if (options || field === "current_student") {
    return (
      <label className="eligibility-answer-field">
        <span>{label}</span>
        <select
          onChange={(event) => onChange(field, event.target.value)}
          value={typeof values[field] === "string" ? values[field] : ""}
        >
          <option value="">Choose an answer</option>
          {(options ?? ["Yes", "No"]).map((option) => (
            <option
              key={option}
              value={
                field === "current_student"
                  ? option === "Yes"
                    ? "true"
                    : "false"
                  : option
              }
            >
              {option}
            </option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <label className="eligibility-answer-field">
      <span>{label}</span>
      <input
        max={field === "age" ? 120 : undefined}
        min={field === "age" ? 0 : field === "household_size" ? 1 : undefined}
        onChange={(event) => onChange(field, event.target.value)}
        type={
          field === "age" || field === "household_size" ? "number" : "text"
        }
        value={typeof values[field] === "string" ? values[field] : ""}
      />
    </label>
  );
}

export function EligibilityAssessmentPage() {
  const { schemeId } = useParams();
  const [scheme, setScheme] = useState<Scheme | null>(null);
  const [assessment, setAssessment] = useState<EligibilityAssessment | null>(
    null,
  );
  const [pageState, setPageState] = useState<PageState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [answerValues, setAnswerValues] = useState<AnswerValues>({});
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setPageState("loading");
    setError(null);
    if (!schemeId) {
      setPageState("not-found");
      return () => {
        active = false;
      };
    }
    Promise.all([
      schemeService.getSchemeById(schemeId),
      schemeService.assessEligibility(schemeId),
    ])
      .then(([loadedScheme, result]) => {
        if (!active) return;
        if (!loadedScheme) {
          setPageState("not-found");
          return;
        }
        setScheme(loadedScheme);
        setAssessment(result);
        setPageState("ready");
      })
      .catch((loadError: unknown) => {
        if (!active) return;
        setError(
          loadError instanceof Error
            ? loadError.message
            : "The assessment could not be loaded.",
        );
        setPageState("error");
      });
    return () => {
      active = false;
    };
  }, [schemeId, reloadKey]);

  const questionFields = useMemo(
    () =>
      [
        ...new Set(
          assessment?.criteria
            .filter(
              (criterion) =>
                criterion.result === "unknown" && criterion.profile_field,
            )
            .map((criterion) => criterion.profile_field as string) ?? [],
        ),
      ],
    [assessment],
  );
  const completedCriteria =
    assessment?.criteria.filter(
      (criterion) =>
        criterion.result === "satisfied" ||
        criterion.result === "not_satisfied",
    ).length ?? 0;
  const progressMax = assessment?.criteria.length ?? 0;

  function updateAnswer(field: string, value: string | string[]) {
    setAnswerValues((current) => ({ ...current, [field]: value }));
  }

  async function reassess(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!schemeId) return;
    setError(null);
    setSubmitting(true);
    try {
      setAssessment(
        await schemeService.assessEligibility(
          schemeId,
          buildAnswers(answerValues),
        ),
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The assessment could not be completed.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (pageState === "loading") {
    return (
      <section aria-live="polite" className="discovery-page">
        <div className="detail-loading">Loading eligibility assessment…</div>
      </section>
    );
  }
  if (pageState === "not-found") {
    return (
      <section className="discovery-page">
        <h1>Scheme record not found</h1>
        <Link className="button button--primary" to="/schemes">
          Back to schemes
        </Link>
      </section>
    );
  }
  if (pageState === "error" || !scheme || !assessment) {
    return (
      <section aria-labelledby="eligibility-load-error" className="discovery-page">
        <Link className="back-link" to={schemeId ? `/schemes/${schemeId}` : "/schemes"}>
          <ArrowLeft aria-hidden="true" size={17} />
          Back to scheme
        </Link>
        <div className="discovery-state discovery-state--error" role="alert">
          <h1 id="eligibility-load-error">Unable to load the assessment</h1>
          <p>{error ?? "Please try again."}</p>
          <button
            className="button button--secondary"
            onClick={() => setReloadKey((current) => current + 1)}
            type="button"
          >
            Try again
          </button>
        </div>
      </section>
    );
  }

  const outcomeLabel: Record<EligibilityAssessment["outcome"], string> = {
    potentially_eligible: "Potentially eligible",
    more_information_required: "More information required",
    known_criteria_not_satisfied: "One or more known criteria not satisfied",
    unable_to_determine: "Unable to determine",
  };
  const unresolvedCount = assessment.criteria.filter(
    (criterion) =>
      criterion.result === "unknown" ||
      criterion.result === "requires_confirmation",
  ).length;

  return (
    <main className="discovery-page eligibility-page">
      <Link className="back-link" to={`/schemes/${scheme.id}`}>
        <ArrowLeft aria-hidden="true" size={17} />
        Back to scheme details
      </Link>
      <header className="eligibility-page-header">
        <p className="eyebrow">Structured criteria review</p>
        <h1>{scheme.name}</h1>
        <p>
          Compare only recorded, supported criteria with your saved profile or
          optional temporary answers.
        </p>
      </header>

      <section
        aria-labelledby="eligibility-result-heading"
        className="eligibility-assessment eligibility-page-result"
      >
        <header>
          <div>
            <p className="eyebrow">
              {assessment.assessment_mode === "saved_profile"
                ? "Using your saved profile"
                : "Using temporary answers"}
            </p>
            <h2 id="eligibility-result-heading">
              Preliminary assessment
            </h2>
            <p>{assessment.summary}</p>
          </div>
          <span
            className={`eligibility-outcome eligibility-outcome--${assessment.outcome}`}
          >
            {outcomeLabel[assessment.outcome]}
          </span>
        </header>

        <div className="eligibility-progress">
          <div>
            <span>Criteria assessed</span>
            <strong>
              {completedCriteria} of {progressMax}
            </strong>
          </div>
          <progress
            aria-label="Criteria assessed"
            max={Math.max(progressMax, 1)}
            value={completedCriteria}
          />
          {unresolvedCount > 0 && (
            <span>
              {unresolvedCount} criterion{unresolvedCount === 1 ? "" : "a"}{" "}
              need{unresolvedCount === 1 ? "s" : ""} more information or
              confirmation.
            </span>
          )}
        </div>

        {assessment.criteria.length > 0 ? (
          <ul className="eligibility-criteria-list">
            {assessment.criteria.map((criterion) => (
              <li key={criterion.rule_id}>
                <span>
                  <strong>{criterion.criterion}</strong>
                  {criterion.profile_field && (
                    <small>
                      Profile field: {fieldLabel(criterion.profile_field)}
                    </small>
                  )}
                  {criterion.evaluated_value !== null &&
                    criterion.evaluated_value !== undefined && (
                      <small>
                        Value assessed:{" "}
                        {Array.isArray(criterion.evaluated_value)
                          ? criterion.evaluated_value.join(", ")
                          : String(criterion.evaluated_value)}
                      </small>
                    )}
                  <span>{criterion.explanation}</span>
                  {criterion.uncertainty_reason && (
                    <small className="eligibility-uncertainty">
                      Why uncertain: {criterion.uncertainty_reason}
                    </small>
                  )}
                  {criterion.rule_source_references.map((source) => (
                    <a
                      className="eligibility-rule-source"
                      href={source.url}
                      key={source.url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      Rule source: {source.title ?? source.url}
                      <ArrowUpRight aria-hidden="true" size={13} />
                    </a>
                  ))}
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
          <p>No reviewed structured criteria are available for this record.</p>
        )}

        {assessment.missing_information.length > 0 && (
          <aside className="eligibility-missing-info">
            <CircleHelp aria-hidden="true" size={18} />
            <span>
              <strong>Information still needed</strong>
              <span>{assessment.missing_information.join(", ")}</span>
            </span>
          </aside>
        )}

        {assessment.sources.length > 0 && (
          <div className="eligibility-sources">
            <strong>Verified scheme sources</strong>
            {assessment.sources.map((source) => (
              <a
                href={source.url}
                key={source.url}
                rel="noreferrer"
                target="_blank"
              >
                {source.title ?? source.url}
                <ArrowUpRight aria-hidden="true" size={13} />
              </a>
            ))}
          </div>
        )}

        <aside className="eligibility-next-action">
          <ShieldCheck aria-hidden="true" size={19} />
          <span>
            <strong>Recommended next action</strong>
            <span>
              {assessment.outcome === "potentially_eligible"
                ? "Verify each requirement with the official source before applying."
                : assessment.outcome === "known_criteria_not_satisfied"
                  ? "Review the criteria marked not satisfied and contact the scheme authority if the rule or your details may be out of date."
                  : assessment.outcome === "more_information_required"
                    ? "Answer the open questions below, or update your saved profile if you want those details retained."
                    : "This record cannot currently support a reliable assessment. Check its official sources or seek confirmation from the relevant authority."}
            </span>
          </span>
        </aside>
        <p className="eligibility-disclaimer">{assessment.disclaimer}</p>
      </section>

      {questionFields.length > 0 && (
        <section
          aria-labelledby="eligibility-questions-heading"
          className="eligibility-questions"
        >
          <div>
            <p className="eyebrow">Optional · not saved to your profile</p>
            <h2 id="eligibility-questions-heading">
              Answer questions for a temporary reassessment
            </h2>
            <p>
              These answers override saved profile values only for this check.
              To keep changes, update your profile separately.
            </p>
          </div>
          <form onSubmit={(event) => void reassess(event)}>
            <div className="eligibility-answer-grid">
              {questionFields.map((field) => (
                <EligibilityAnswerField
                  field={field}
                  key={field}
                  onChange={updateAnswer}
                  values={answerValues}
                />
              ))}
            </div>
            {error && (
              <p className="inline-error" role="alert">
                {error}
              </p>
            )}
            <button
              className="button button--primary"
              disabled={submitting}
              type="submit"
            >
              {submitting ? (
                <>
                  <LoaderCircle aria-hidden="true" className="spin" size={16} />
                  Reassessing…
                </>
              ) : (
                "Reassess with temporary answers"
              )}
            </button>
          </form>
        </section>
      )}

      <Link className="button button--secondary eligibility-profile-link" to="/profile">
        Update saved profile
      </Link>
      <p className="eligibility-page-note">
        A preliminary match is not an approval or a final eligibility decision.
        Confirm scheme rules, dates, and application instructions with the
        responsible government authority.
      </p>
      <span className="visually-hidden" aria-live="polite">
        {submitting ? "Assessment in progress" : "Assessment complete"}
      </span>
    </main>
  );
}
