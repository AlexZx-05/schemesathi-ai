import { useEffect, useState } from "react";
import {
  CircleUserRound,
  PencilLine,
  ShieldCheck,
  Sprout,
  UserRound,
} from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { authService } from "../lib/auth";
import type { Profile, ProfileInput } from "../lib/auth";

const steps = [
  {
    path: "welcome",
    title: "Welcome",
    description: "How we use your information",
  },
  {
    path: "personal",
    title: "Personal",
    description: "A few details about you",
  },
  {
    path: "education",
    title: "Education",
    description: "Your education background",
  },
  {
    path: "family",
    title: "Family",
    description: "Optional household details",
  },
  { path: "location", title: "Location", description: "Where you live" },
  {
    path: "additional-details",
    title: "Additional details",
    description: "Work and relevant groups",
  },
  { path: "review", title: "Review", description: "Check and finish" },
] as const;

interface OnboardingValues {
  full_name: string;
  age: string;
  education_level: string;
  current_student: string;
  annual_income_range: string;
  household_size: string;
  state: string;
  district: string;
  area_type: string;
  occupation: string;
  occupation_other: string;
  employment_status: string;
  worker_category: string;
  beneficiary_categories: string[];
}

const emptyValues: OnboardingValues = {
  full_name: "",
  age: "",
  education_level: "",
  current_student: "",
  annual_income_range: "",
  household_size: "",
  state: "",
  district: "",
  area_type: "",
  occupation: "",
  occupation_other: "",
  employment_status: "",
  worker_category: "",
  beneficiary_categories: [],
};

const states = [
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
] as const;

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
const incomeRanges = [
  "Prefer not to say",
  "Below ₹1 lakh",
  "₹1–3 lakh",
  "₹3–6 lakh",
  "₹6–10 lakh",
  "Above ₹10 lakh",
] as const;
const beneficiaryCategories = [
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
] as const;

function fromProfile(profile: Profile): OnboardingValues {
  return {
    full_name: profile.full_name,
    age: profile.age?.toString() ?? "",
    education_level: profile.education_level ?? "",
    current_student:
      profile.current_student === null ? "" : String(profile.current_student),
    annual_income_range: profile.annual_income_range ?? "",
    household_size: profile.household_size?.toString() ?? "",
    state: profile.state ?? "",
    district: profile.district ?? "",
    area_type: profile.area_type ?? "",
    occupation: profile.occupation ?? "",
    occupation_other: profile.occupation_other ?? "",
    employment_status: profile.employment_status ?? "",
    worker_category: profile.worker_category ?? "",
    beneficiary_categories: profile.beneficiary_categories,
  };
}

function toProfileInput(values: OnboardingValues): ProfileInput {
  return {
    full_name: values.full_name.trim() || undefined,
    age: values.age ? Number(values.age) : null,
    education_level: values.education_level || null,
    current_student: values.current_student
      ? values.current_student === "true"
      : null,
    annual_income_range: values.annual_income_range || null,
    household_size: values.household_size
      ? Number(values.household_size)
      : null,
    state: values.state || null,
    district: values.district.trim() || null,
    area_type: values.area_type || null,
    occupation: values.occupation || null,
    occupation_other:
      values.occupation === "Other"
        ? values.occupation_other.trim() || null
        : null,
    employment_status: values.employment_status || null,
    worker_category: values.worker_category.trim() || null,
    beneficiary_categories: values.beneficiary_categories,
  };
}

function SelectField({
  id,
  label,
  value,
  options,
  onChange,
  required = false,
}: {
  id: string;
  label: string;
  value: string;
  options: readonly string[];
  onChange: (value: string) => void;
  required?: boolean;
}) {
  return (
    <label className="onboarding-field" htmlFor={id}>
      {label}
      {required && <span aria-hidden="true"> *</span>}
      <select
        id={id}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        value={value}
      >
        <option value="">Choose an option</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

export function OnboardingPage() {
  const { step = "welcome" } = useParams();
  const navigate = useNavigate();
  const { user, updateUser } = useAuth();
  const currentIndex = Math.max(
    0,
    steps.findIndex((item) => item.path === step),
  );
  const current = steps[currentIndex];
  const [values, setValues] = useState(emptyValues);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    authService
      .getProfile()
      .then((profile) => {
        if (active) setValues(fromProfile(profile));
      })
      .catch((requestError: unknown) => {
        if (active)
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Could not load your profile.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function update<K extends keyof OnboardingValues>(
    key: K,
    value: OnboardingValues[K],
  ) {
    setSaved(false);
    setValues((previous) => ({ ...previous, [key]: value }));
  }

  async function saveProgress(): Promise<Profile | null> {
    setError(null);
    setSaving(true);
    try {
      const profile = await authService.updateProfile(toProfileInput(values));
      if (user)
        updateUser({
          ...user,
          full_name: profile.full_name,
          profile_complete: profile.profile_complete,
        });
      setSaved(true);
      return profile;
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not save your progress.",
      );
      return null;
    } finally {
      setSaving(false);
    }
  }

  function validateStep(): boolean {
    if (step === "personal" && values.full_name.trim().length < 2) {
      setFieldError("Enter your full name.");
      return false;
    }
    if (
      step === "personal" &&
      values.age &&
      (!Number.isInteger(Number(values.age)) ||
        Number(values.age) < 18 ||
        Number(values.age) > 120)
    ) {
      setFieldError("Age must be between 18 and 120, or leave it blank.");
      return false;
    }
    if (step === "education" && !values.education_level) {
      setFieldError("Choose your highest education level.");
      return false;
    }
    if (step === "location" && !values.state) {
      setFieldError("Choose your state or union territory.");
      return false;
    }
    if (step === "additional-details" && !values.occupation) {
      setFieldError("Choose an occupation, or select Other.");
      return false;
    }
    if (
      step === "additional-details" &&
      values.occupation === "Other" &&
      !values.occupation_other.trim()
    ) {
      setFieldError("Describe your occupation.");
      return false;
    }
    setFieldError(null);
    return true;
  }

  async function continueOnboarding() {
    if (!validateStep()) return;
    const profile = await saveProgress();
    if (!profile) return;
    navigate(
      `/onboarding/${steps[Math.min(currentIndex + 1, steps.length - 1)].path}`,
    );
  }

  async function finishOnboarding() {
    const profile = await saveProgress();
    if (!profile) return;
    if (!profile.profile_complete) {
      setFieldError(
        "Please provide your state, education level, and occupation to finish. You can skip the optional questions.",
      );
      return;
    }
    navigate("/dashboard", { replace: true });
  }

  async function saveAndExit() {
    const profile = await saveProgress();
    if (profile) navigate("/dashboard");
  }

  const setCategory = (category: string, checked: boolean) => {
    update(
      "beneficiary_categories",
      checked
        ? [...values.beneficiary_categories, category]
        : values.beneficiary_categories.filter((item) => item !== category),
    );
  };

  if (loading)
    return (
      <div aria-live="polite" className="auth-loading">
        Loading your saved progress…
      </div>
    );

  return (
    <section
      aria-label="Profile setup"
      className="profile-onboarding onboarding-split"
    >
      <aside
        aria-label="Profile setup benefits"
        className="profile-intro-panel"
      >
        <div
          aria-label="Indian students and family in front of the Parliament and India Gate"
          className="profile-intro-art onboarding-hero-art"
          role="img"
        />
        <div className="profile-intro-content onboarding-hero-content">
          <p className="profile-step-badge">
            <CircleUserRound aria-hidden="true" size={16} />
            Step {currentIndex + 1} of {steps.length} · Profile Setup
          </p>
          <h1 className="onboarding-hero-title">
            Let’s Prepare
            <span>Your Profile</span>
          </h1>
          <p className="profile-intro-description">
            Share a few details to help us organize relevant government scheme
            information for you.
          </p>
          <ul className="profile-benefits">
            <li>
              <span className="profile-benefit-icon profile-benefit-icon--blue">
                <UserRound aria-hidden="true" size={21} />
              </span>
              <span>
                <strong>Personalized discovery</strong>
                <span>See scheme information organized around your needs.</span>
              </span>
            </li>
            <li>
              <span className="profile-benefit-icon profile-benefit-icon--green">
                <ShieldCheck aria-hidden="true" size={21} />
              </span>
              <span>
                <strong>Your information stays private</strong>
                <span>Only share details you are comfortable providing.</span>
              </span>
            </li>
            <li>
              <span className="profile-benefit-icon profile-benefit-icon--purple">
                <PencilLine aria-hidden="true" size={21} />
              </span>
              <span>
                <strong>Update it anytime</strong>
                <span>Your profile can be changed or removed later.</span>
              </span>
            </li>
          </ul>
          <div className="profile-illustration-badge">
            <Sprout aria-hidden="true" size={18} />
            <span>Government schemes for a brighter India</span>
          </div>
        </div>
      </aside>

      <div className="profile-form-panel onboarding-form-panel">
        <header className="onboarding-header">
          <div className="onboarding-heading-row">
            <div>
              <p className="onboarding-eyebrow">
                Profile setup · Step {currentIndex + 1} of {steps.length}
              </p>
              <h1 id="onboarding-title">{current.title}</h1>
              <p>{current.description}</p>
            </div>
            <button
              className="button button--secondary onboarding-save-exit"
              disabled={saving}
              onClick={saveAndExit}
              type="button"
            >
              {saving ? "Saving…" : "Save and exit"}
            </button>
          </div>
          <ol
            aria-label="Onboarding progress"
            className="onboarding-wizard-progress"
          >
            {steps.map((item, index) => (
              <li
                aria-current={index === currentIndex ? "step" : undefined}
                className={index <= currentIndex ? "is-complete" : ""}
                key={item.path}
              >
                <span aria-hidden="true" className="onboarding-step-marker">
                  {index + 1}
                </span>
                <span className="onboarding-step-label">{item.title}</span>
              </li>
            ))}
          </ol>
        </header>

        {error && (
          <p className="form-error-banner" role="alert">
            {error}
          </p>
        )}
        {fieldError && (
          <p className="form-error-banner" role="alert">
            {fieldError}
          </p>
        )}
        {saved && (
          <p className="workflow-success" role="status">
            Your progress has been saved.
          </p>
        )}

        <div className="onboarding-body">
          {step === "welcome" && (
            <div className="onboarding-intro">
              <h2>Share only what helps organize scheme discovery</h2>
              <p>
                Some schemes use location, education, or work details to
                describe possible eligibility. Your profile is for organizing
                information only; it does not determine eligibility.
              </p>
              <div className="privacy-notice">
                <strong>Privacy notice</strong>
                <p>
                  Age, district, education, work, and optional household details
                  are used to personalize scheme information. Skip optional
                  questions or update your profile later.
                </p>
                <p>
                  Never provide Aadhaar numbers, bank account numbers,
                  government-portal passwords, or other unnecessary sensitive
                  information.
                </p>
              </div>
            </div>
          )}
          {step === "personal" && (
            <div className="onboarding-fields">
              <label className="onboarding-field" htmlFor="onboarding-name">
                Full name *
                <input
                  autoComplete="name"
                  id="onboarding-name"
                  maxLength={100}
                  onChange={(event) => update("full_name", event.target.value)}
                  required
                  value={values.full_name}
                />
              </label>
              <label className="onboarding-field" htmlFor="onboarding-age">
                Age <span className="field-optional">(optional)</span>
                <input
                  id="onboarding-age"
                  inputMode="numeric"
                  max="120"
                  min="18"
                  onChange={(event) => update("age", event.target.value)}
                  type="number"
                  value={values.age}
                />
              </label>
              <p className="onboarding-help">
                We do not need a date of birth. Providing age is optional unless
                you choose to use it when reviewing scheme information.
              </p>
            </div>
          )}
          {step === "education" && (
            <div className="onboarding-fields">
              <SelectField
                id="education-level"
                label="Highest education level"
                onChange={(value) => update("education_level", value)}
                options={educationLevels}
                required
                value={values.education_level}
              />
              <fieldset className="onboarding-choice">
                <legend>
                  Are you currently a student?{" "}
                  <span className="field-optional">(optional)</span>
                </legend>
                <label>
                  <input
                    checked={values.current_student === "true"}
                    name="current-student"
                    onChange={() => update("current_student", "true")}
                    type="radio"
                  />{" "}
                  Yes
                </label>
                <label>
                  <input
                    checked={values.current_student === "false"}
                    name="current-student"
                    onChange={() => update("current_student", "false")}
                    type="radio"
                  />{" "}
                  No
                </label>
                <label>
                  <input
                    checked={!values.current_student}
                    name="current-student"
                    onChange={() => update("current_student", "")}
                    type="radio"
                  />{" "}
                  Skip
                </label>
              </fieldset>
            </div>
          )}
          {step === "family" && (
            <div className="onboarding-fields">
              <SelectField
                id="income-range"
                label="Annual family income range (optional)"
                onChange={(value) => update("annual_income_range", value)}
                options={incomeRanges}
                value={values.annual_income_range}
              />
              <label className="onboarding-field" htmlFor="household-size">
                Household size{" "}
                <span className="field-optional">(optional)</span>
                <input
                  id="household-size"
                  max="30"
                  min="1"
                  onChange={(event) =>
                    update("household_size", event.target.value)
                  }
                  type="number"
                  value={values.household_size}
                />
              </label>
              <p className="onboarding-help">
                You may choose “Prefer not to say” or leave these fields blank.
                No exact income amount is requested.
              </p>
            </div>
          )}
          {step === "location" && (
            <div className="onboarding-fields">
              <SelectField
                id="state"
                label="State or union territory"
                onChange={(value) => update("state", value)}
                options={states}
                required
                value={values.state}
              />
              <label className="onboarding-field" htmlFor="district">
                District <span className="field-optional">(optional)</span>
                <input
                  autoComplete="address-level2"
                  id="district"
                  maxLength={100}
                  onChange={(event) => update("district", event.target.value)}
                  value={values.district}
                />
              </label>
              <SelectField
                id="area-type"
                label="Area type (optional)"
                onChange={(value) => update("area_type", value)}
                options={["Rural", "Urban"]}
                value={values.area_type}
              />
            </div>
          )}
          {step === "additional-details" && (
            <div className="onboarding-fields">
              <SelectField
                id="occupation"
                label="Occupation"
                onChange={(value) => update("occupation", value)}
                options={[
                  "Student",
                  "Farmer",
                  "Salaried employee",
                  "Self-employed",
                  "Job seeker",
                  "Homemaker",
                  "Other",
                ]}
                required
                value={values.occupation}
              />
              {values.occupation === "Other" && (
                <label className="onboarding-field" htmlFor="occupation-other">
                  Describe your occupation
                  <input
                    id="occupation-other"
                    maxLength={80}
                    onChange={(event) =>
                      update("occupation_other", event.target.value)
                    }
                    required
                    value={values.occupation_other}
                  />
                </label>
              )}
              <SelectField
                id="employment-status"
                label="Employment status (optional)"
                onChange={(value) => update("employment_status", value)}
                options={[
                  "Employed",
                  "Self-employed",
                  "Unemployed",
                  "Student",
                  "Homemaker",
                  "Other",
                ]}
                value={values.employment_status}
              />
              <label className="onboarding-field" htmlFor="worker-category">
                Worker or farmer category (optional)
                <input
                  id="worker-category"
                  maxLength={80}
                  onChange={(event) =>
                    update("worker_category", event.target.value)
                  }
                  value={values.worker_category}
                />
              </label>
              <fieldset className="onboarding-choice">
                <legend>
                  Relevant beneficiary groups{" "}
                  <span className="field-optional">(optional)</span>
                </legend>
                {beneficiaryCategories.map((category) => (
                  <label key={category}>
                    <input
                      checked={values.beneficiary_categories.includes(category)}
                      onChange={(event) =>
                        setCategory(category, event.target.checked)
                      }
                      type="checkbox"
                    />
                    {category}
                  </label>
                ))}
              </fieldset>
            </div>
          )}
          {step === "review" && (
            <div className="onboarding-review">
              <p>
                Check your information. You can go back to make changes;
                optional answers can remain blank.
              </p>
              <dl>
                <dt>Full name</dt>
                <dd>{values.full_name || "Not provided"}</dd>
                <dt>Age</dt>
                <dd>{values.age || "Skipped"}</dd>
                <dt>Education</dt>
                <dd>{values.education_level || "Not provided"}</dd>
                <dt>Location</dt>
                <dd>
                  {[values.district, values.state, values.area_type]
                    .filter(Boolean)
                    .join(", ") || "Not provided"}
                </dd>
                <dt>Occupation</dt>
                <dd>
                  {values.occupation === "Other"
                    ? values.occupation_other
                    : values.occupation || "Not provided"}
                </dd>
                <dt>Family income range</dt>
                <dd>{values.annual_income_range || "Skipped"}</dd>
                <dt>Beneficiary groups</dt>
                <dd>{values.beneficiary_categories.join(", ") || "Skipped"}</dd>
              </dl>
              <p className="onboarding-help">
                You can edit or remove this information later in your profile.
              </p>
            </div>
          )}
        </div>

        <footer className="onboarding-actions">
          {currentIndex > 0 ? (
            <button
              className="button button--secondary"
              disabled={saving}
              onClick={() =>
                navigate(`/onboarding/${steps[currentIndex - 1].path}`)
              }
              type="button"
            >
              Back
            </button>
          ) : (
            <span />
          )}
          {step === "review" ? (
            <button
              className="button button--primary"
              disabled={saving}
              onClick={finishOnboarding}
              type="button"
            >
              {saving ? "Saving…" : "Complete profile"}
            </button>
          ) : (
            <button
              className="button button--primary"
              disabled={saving}
              onClick={continueOnboarding}
              type="button"
            >
              {saving ? "Saving…" : "Continue"}
            </button>
          )}
        </footer>
      </div>
    </section>
  );
}
