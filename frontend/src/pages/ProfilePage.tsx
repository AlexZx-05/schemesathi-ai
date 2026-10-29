import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  CircleUserRound,
  GraduationCap,
  PencilLine,
  ShieldCheck,
  Sprout,
  UserRound,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import type { FieldPath } from "react-hook-form";
import { z } from "zod";

import { TextField } from "../components/ui/TextField";
import { useAuth } from "../context/AuthContext";
import { authService } from "../lib/auth";
import type { Profile, ProfileInput } from "../lib/auth";

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

const jobInterestLimit = 10;

const occupations = [
  "Student",
  "Farmer",
  "Salaried employee",
  "Self-employed",
  "Job seeker",
  "Homemaker",
  "Other",
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

const profileSchema = z
  .object({
    full_name: z
      .string()
      .trim()
      .min(2, "Enter your name.")
      .max(100, "Name must be 100 characters or fewer."),
    age: z.preprocess(
      (value) =>
        value === "" ||
        value === undefined ||
        value === null ||
        Number.isNaN(value)
          ? null
          : value,
      z.number().int().min(18).max(120).nullable(),
    ),
    state: z
      .string()
      .refine((value) => states.some((state) => state === value), {
        message: "Choose your state or territory.",
      }),
    occupation: z
      .string()
      .refine((value) => occupations.some((item) => item === value), {
        message: "Choose an occupation.",
      }),
    occupation_other: z.string().trim().max(80).nullable(),
    education_level: z
      .string()
      .refine((value) => educationLevels.some((item) => item === value), {
        message: "Choose your education level.",
      }),
    qualification: z.string().trim().max(120),
    field_of_study: z.string().trim().max(120),
    years_experience: z.preprocess(
      (value) =>
        value === "" ||
        value === undefined ||
        value === null ||
        Number.isNaN(value)
          ? null
          : value,
      z.number().int().min(0).max(60).nullable(),
    ),
    preferred_job_roles: z.string().max(800),
    preferred_job_states: z.array(z.enum(states)).max(states.length),
    annual_income_range: z.union([z.literal(""), z.enum(incomeRanges)]),
    beneficiary_categories: z
      .array(z.enum(beneficiaryCategories))
      .max(10, "Choose no more than 10 categories."),
  })
  .superRefine((values, context) => {
    if (values.occupation === "Other" && !values.occupation_other?.trim()) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Describe your occupation.",
        path: ["occupation_other"],
      });
    }
  });

type ProfileValues = z.infer<typeof profileSchema>;

const steps = [
  { label: "Basic Details", description: "A few details about you" },
  { label: "Family Details", description: "Optional income information" },
  { label: "Additional Info", description: "Groups you identify with" },
  { label: "Job Preferences", description: "Optional matching details" },
  { label: "Review", description: "Check and save your profile" },
] as const;

const stepFields: FieldPath<ProfileValues>[][] = [
  [
    "full_name",
    "age",
    "state",
    "occupation",
    "occupation_other",
    "education_level",
  ],
  ["annual_income_range"],
  ["beneficiary_categories"],
  [
    "qualification",
    "field_of_study",
    "years_experience",
    "preferred_job_roles",
    "preferred_job_states",
  ],
  [],
];

function toFormValues(profile: Profile): ProfileValues {
  return {
    full_name: profile.full_name,
    age: profile.age,
    state: profile.state ?? "",
    occupation: profile.occupation ?? "",
    occupation_other: profile.occupation_other ?? "",
    education_level: profile.education_level ?? "",
    qualification: profile.qualification ?? "",
    field_of_study: profile.field_of_study ?? "",
    years_experience: profile.years_experience,
    preferred_job_roles: profile.preferred_job_roles.join("\n"),
    preferred_job_states: profile.preferred_job_states.filter(
      (state): state is (typeof states)[number] =>
        states.some((allowed) => allowed === state),
    ),
    annual_income_range:
      incomeRanges.find((item) => item === profile.annual_income_range) ?? "",
    beneficiary_categories: profile.beneficiary_categories.filter(
      (category): category is (typeof beneficiaryCategories)[number] =>
        beneficiaryCategories.some((allowed) => allowed === category),
    ),
  };
}

export function ProfilePage() {
  const { user, updateUser } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const {
    register,
    handleSubmit,
    reset,
    trigger,
    watch,
    getValues,
    formState: { errors },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: "",
      age: null,
      state: "",
      occupation: "",
      occupation_other: "",
      education_level: "",
      qualification: "",
      field_of_study: "",
      years_experience: null,
      preferred_job_roles: "",
      preferred_job_states: [],
      annual_income_range: "",
      beneficiary_categories: [],
    },
  });
  const occupation = watch("occupation");
  const selectedCategories = watch("beneficiary_categories") ?? [];

  useEffect(() => {
    let active = true;
    authService
      .getProfile()
      .then((loadedProfile) => {
        if (!active) return;
        setProfile(loadedProfile);
        reset(toFormValues(loadedProfile));
      })
      .catch((error: unknown) => {
        if (!active) return;
        setLoadError(
          error instanceof Error
            ? error.message
            : "We couldn’t load your profile.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reset]);

  async function goToNextStep() {
    const valid = await trigger(stepFields[activeStep]);
    if (valid) {
      setSaveError(null);
      setSaved(false);
      setActiveStep((step) => Math.min(step + 1, steps.length - 1));
    }
  }

  async function onSubmit(values: ProfileValues) {
    setSaveError(null);
    setSaved(false);
    setSaving(true);
    const payload: ProfileInput = {
      ...values,
      annual_income_range: values.annual_income_range || null,
      qualification: values.qualification || null,
      field_of_study: values.field_of_study || null,
      preferred_job_roles: values.preferred_job_roles
        .split(/\r?\n/)
        .map((role) => role.trim())
        .filter(Boolean)
        .slice(0, jobInterestLimit),
      occupation_other:
        values.occupation === "Other" ? values.occupation_other : null,
    };
    try {
      const updatedProfile = await authService.updateProfile(payload);
      setProfile(updatedProfile);
      reset(toFormValues(updatedProfile));
      if (user) {
        updateUser({
          ...user,
          full_name: updatedProfile.full_name,
          profile_complete: updatedProfile.profile_complete,
        });
      }
      setSaved(true);
    } catch (error) {
      setSaveError(
        error instanceof Error
          ? error.message
          : "We couldn’t save your profile. Please try again.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div aria-live="polite" className="auth-loading">
        Loading your profile…
      </div>
    );
  }

  if (loadError || !profile) {
    return (
      <section aria-labelledby="profile-error-title" className="auth-page">
        <div className="auth-card auth-card--notice" role="alert">
          <h1 id="profile-error-title">We couldn’t load your profile</h1>
          <p>{loadError ?? "Please sign in again and retry."}</p>
        </div>
      </section>
    );
  }

  const values = getValues();
  const categorySummary = selectedCategories.length
    ? selectedCategories.join(", ")
    : "None selected";

  return (
    <section aria-labelledby="profile-title" className="profile-onboarding">
      <aside
        aria-label="Profile setup benefits"
        className="profile-intro-panel"
      >
        <div
          aria-label="Illustration of Indian citizens, Parliament, and India Gate"
          className="profile-intro-art"
          role="img"
        />
        <div className="profile-intro-content">
          <p className="profile-step-badge">
            <CircleUserRound aria-hidden="true" size={16} />
            Step 1 of 5 · Profile Setup
          </p>
          <h1 id="profile-title">
            Let’s Prepare
            <span>Your Profile</span>
          </h1>
          <p className="profile-intro-description">
            This helps us find relevant schemes and central government jobs.
          </p>

          <ul className="profile-benefits">
            <li>
              <span className="profile-benefit-icon profile-benefit-icon--blue">
                <UserRound aria-hidden="true" size={22} />
              </span>
              <span>
                <strong>Personalized recommendations</strong>
                <span>
                  Explore information that fits your profile and needs.
                </span>
              </span>
            </li>
            <li>
              <span className="profile-benefit-icon profile-benefit-icon--green">
                <ShieldCheck aria-hidden="true" size={22} />
              </span>
              <span>
                <strong>Your information stays private</strong>
                <span>
                  Your details are used to organize relevant scheme and job
                  information.
                </span>
              </span>
            </li>
            <li>
              <span className="profile-benefit-icon profile-benefit-icon--purple">
                <PencilLine aria-hidden="true" size={22} />
              </span>
              <span>
                <strong>You can update this anytime</strong>
                <span>Keep your profile current as your needs change.</span>
              </span>
            </li>
          </ul>
          <div className="profile-illustration-badge">
            <Sprout aria-hidden="true" size={18} />
            <span>Government schemes for a brighter India</span>
          </div>
        </div>
      </aside>

      <div className="profile-form-panel">
        <nav
          aria-label="Profile setup progress"
          className="onboarding-progress"
        >
          {steps.map((step, index) => {
            const isComplete = index < activeStep;
            const isCurrent = index === activeStep;
            return (
              <div
                aria-current={isCurrent ? "step" : undefined}
                className={`onboarding-progress-step${
                  isCurrent ? "is-current" : ""
                }${isComplete ? "is-complete" : ""}`}
                key={step.label}
              >
                <span aria-hidden="true" className="onboarding-step-marker">
                  {isComplete ? <Check size={16} /> : index + 1}
                </span>
                <span className="onboarding-step-label">{step.label}</span>
              </div>
            );
          })}
        </nav>

        <div className="profile-form-heading">
          <span className="profile-form-icon">
            {activeStep === 0 ? (
              <CircleUserRound aria-hidden="true" size={21} />
            ) : activeStep === 1 ? (
              <ShieldCheck aria-hidden="true" size={21} />
            ) : activeStep === 2 ? (
              <GraduationCap aria-hidden="true" size={21} />
            ) : activeStep === 3 ? (
              <GraduationCap aria-hidden="true" size={21} />
            ) : (
              <CheckCircle2 aria-hidden="true" size={21} />
            )}
          </span>
          <div>
            <p className="eyebrow">
              Step {activeStep + 1} of {steps.length}
            </p>
            <h2>{steps[activeStep].label}</h2>
            <p>{steps[activeStep].description}</p>
          </div>
        </div>

        <form
          className="profile-wizard-form"
          noValidate
          onSubmit={handleSubmit(onSubmit)}
        >
          {activeStep === 0 && (
            <div className="profile-field-grid">
              <TextField
                autoComplete="name"
                error={errors.full_name?.message}
                id="profile-name"
                label="Full name"
                required
                {...register("full_name")}
              />
              <TextField
                autoComplete="email"
                hint="Your sign-in email can’t be changed here."
                id="profile-email"
                label="Email address"
                readOnly
                value={profile.email}
              />
              <label className="field">
                <span className="field-label">Age (optional)</span>
                <input
                  aria-describedby={
                    errors.age ? "profile-age-error" : "profile-age-hint"
                  }
                  aria-invalid={errors.age ? true : undefined}
                  className="field-input"
                  id="profile-age"
                  inputMode="numeric"
                  max="120"
                  min="18"
                  placeholder="Leave blank if you prefer"
                  type="number"
                  {...register("age", {
                    setValueAs: (value: string) =>
                      value === "" || value === null || value === undefined
                        ? null
                        : Number(value),
                  })}
                />
                {errors.age ? (
                  <span
                    className="field-error"
                    id="profile-age-error"
                    role="alert"
                  >
                    Enter an age from 18 to 120, or leave it blank.
                  </span>
                ) : (
                  <span className="field-hint" id="profile-age-hint">
                    Only share this if you’re comfortable.
                  </span>
                )}
              </label>
              <label className="field">
                <span className="field-label">State or union territory *</span>
                <select
                  aria-invalid={errors.state ? true : undefined}
                  className="field-input"
                  id="profile-state"
                  {...register("state")}
                >
                  <option disabled value="">
                    Choose your state or union territory
                  </option>
                  {states.map((state) => (
                    <option key={state} value={state}>
                      {state}
                    </option>
                  ))}
                </select>
                {errors.state && (
                  <span className="field-error" role="alert">
                    {errors.state.message}
                  </span>
                )}
              </label>
              <label className="field">
                <span className="field-label">Occupation *</span>
                <select
                  aria-invalid={errors.occupation ? true : undefined}
                  className="field-input"
                  id="profile-occupation"
                  {...register("occupation")}
                >
                  <option disabled value="">
                    Choose an occupation
                  </option>
                  {occupations.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
                {errors.occupation && (
                  <span className="field-error" role="alert">
                    {errors.occupation.message}
                  </span>
                )}
              </label>
              {occupation === "Other" && (
                <TextField
                  error={errors.occupation_other?.message}
                  id="profile-occupation-other"
                  label="Describe your occupation"
                  required
                  {...register("occupation_other")}
                />
              )}
              <label className="field">
                <span className="field-label">Education level *</span>
                <select
                  aria-invalid={errors.education_level ? true : undefined}
                  className="field-input"
                  id="profile-education"
                  {...register("education_level")}
                >
                  <option disabled value="">
                    Choose an education level
                  </option>
                  {educationLevels.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
                {errors.education_level && (
                  <span className="field-error" role="alert">
                    {errors.education_level.message}
                  </span>
                )}
              </label>
            </div>
          )}

          {activeStep === 1 && (
            <section className="profile-step-section">
              <label className="field">
                <span className="field-label">
                  Annual family income (optional)
                </span>
                <select
                  aria-describedby="profile-income-hint"
                  aria-invalid={errors.annual_income_range ? true : undefined}
                  className="field-input"
                  id="profile-income"
                  {...register("annual_income_range")}
                >
                  <option value="">Skip this optional question</option>
                  {incomeRanges.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
                {errors.annual_income_range && (
                  <span className="field-error" role="alert">
                    {errors.annual_income_range.message}
                  </span>
                )}
                <span className="field-hint" id="profile-income-hint">
                  You can choose “Prefer not to say”. We don’t ask for an exact
                  amount.
                </span>
              </label>
              <div className="profile-information-note">
                <ShieldCheck aria-hidden="true" size={18} />
                <p>
                  This optional context helps you review relevant scheme
                  information. It does not decide eligibility.
                </p>
              </div>
            </section>
          )}

          {activeStep === 2 && (
            <fieldset className="profile-step-section beneficiary-section">
              <legend>Beneficiary groups (optional)</legend>
              <p className="field-hint">
                Select any groups you identify with. You can change these
                selections later.
              </p>
              <div className="beneficiary-options">
                {beneficiaryCategories.map((category) => (
                  <label className="checkbox-option" key={category}>
                    <input
                      type="checkbox"
                      value={category}
                      {...register("beneficiary_categories")}
                    />
                    <span>{category}</span>
                  </label>
                ))}
              </div>
              {errors.beneficiary_categories && (
                <p className="field-error" role="alert">
                  {errors.beneficiary_categories.message}
                </p>
              )}
              <p aria-live="polite" className="beneficiary-selection-count">
                {selectedCategories.length} selected
              </p>
            </fieldset>
          )}

          {activeStep === 3 && (
            <section aria-label="Optional job preferences" className="profile-step-section">
              <p className="field-hint">
                These optional details improve job matching. Leave any field
                blank if you prefer; reservation or caste category is not
                collected.
              </p>
              <div className="profile-field-grid">
                <TextField
                  error={errors.qualification?.message}
                  id="profile-qualification"
                  label="Qualification or certificate (optional)"
                  maxLength={120}
                  {...register("qualification")}
                />
                <TextField
                  error={errors.field_of_study?.message}
                  id="profile-field-of-study"
                  label="Subject or field of study (optional)"
                  maxLength={120}
                  {...register("field_of_study")}
                />
                <label className="field">
                  <span className="field-label">Years of experience (optional)</span>
                  <input
                    className="field-input"
                    id="profile-years-experience"
                    max="60"
                    min="0"
                    placeholder="Leave blank if not applicable"
                    type="number"
                    {...register("years_experience", {
                      setValueAs: (value: string) =>
                        value === "" || value === null || value === undefined
                          ? null
                          : Number(value),
                    })}
                  />
                </label>
                <label className="field">
                  <span className="field-label">Job interests (optional)</span>
                  <textarea
                    className="field-input"
                    id="profile-job-interests"
                    maxLength={800}
                    placeholder={"For example: engineering\nadministration"}
                    rows={4}
                    {...register("preferred_job_roles")}
                  />
                  <span className="field-hint">
                    Enter up to {jobInterestLimit} roles or areas, one per line.
                  </span>
                </label>
                <label className="field">
                  <span className="field-label">
                    Preferred job locations (optional)
                  </span>
                  <select
                    className="field-input"
                    id="profile-job-locations"
                    multiple
                    size={5}
                    {...register("preferred_job_states")}
                  >
                    {states.map((state) => (
                      <option key={state} value={state}>
                        {state}
                      </option>
                    ))}
                  </select>
                  <span className="field-hint">
                    Leave blank to use your profile state or include nationwide
                    opportunities.
                  </span>
                </label>
              </div>
            </section>
          )}

          {activeStep === 4 && (
            <section aria-label="Profile summary" className="profile-review">
              <dl>
                <div>
                  <dt>Full name</dt>
                  <dd>{values.full_name || "Not provided"}</dd>
                </div>
                <div>
                  <dt>Email address</dt>
                  <dd>{profile.email}</dd>
                </div>
                <div>
                  <dt>Age</dt>
                  <dd>{values.age ? `${values.age} years` : "Not provided"}</dd>
                </div>
                <div>
                  <dt>State or union territory</dt>
                  <dd>{values.state || "Not provided"}</dd>
                </div>
                <div>
                  <dt>Occupation</dt>
                  <dd>
                    {values.occupation === "Other"
                      ? values.occupation_other || "Other"
                      : values.occupation || "Not provided"}
                  </dd>
                </div>
                <div>
                  <dt>Education level</dt>
                  <dd>{values.education_level || "Not provided"}</dd>
                </div>
                <div>
                  <dt>Annual family income</dt>
                  <dd>{values.annual_income_range || "Not provided"}</dd>
                </div>
                <div>
                  <dt>Beneficiary groups</dt>
                  <dd>{categorySummary}</dd>
                </div>
                <div>
                  <dt>Job qualification</dt>
                  <dd>{values.qualification || "Not provided"}</dd>
                </div>
                <div>
                  <dt>Field of study</dt>
                  <dd>{values.field_of_study || "Not provided"}</dd>
                </div>
                <div>
                  <dt>Years of experience</dt>
                  <dd>
                    {values.years_experience === null
                      ? "Not provided"
                      : values.years_experience}
                  </dd>
                </div>
                <div>
                  <dt>Job interests</dt>
                  <dd>
                    {values.preferred_job_roles.trim() || "Not provided"}
                  </dd>
                </div>
                <div>
                  <dt>Preferred job locations</dt>
                  <dd>
                    {values.preferred_job_states.join(", ") || "Use profile state"}
                  </dd>
                </div>
              </dl>
              <div className="profile-information-note">
                <ShieldCheck aria-hidden="true" size={18} />
                <p>
                  Your profile can help you find potentially relevant schemes.
                  It does not guarantee eligibility or benefits. Always confirm
                  requirements with the official source.
                </p>
              </div>
            </section>
          )}

          <p className="profile-privacy-note">
            We don’t ask for Aadhaar numbers, bank details, caste, or exact
            income. Your profile is editable from your account.
          </p>

          {saveError && (
            <p className="form-error-banner" role="alert">
              {saveError}
            </p>
          )}
          {saved && (
            <p className="form-success-banner" role="status">
              <CheckCircle2 aria-hidden="true" size={18} />
              Profile saved.
            </p>
          )}

          <div className="profile-wizard-actions">
            {activeStep > 0 ? (
              <button
                className="button button--secondary"
                onClick={() => setActiveStep((step) => step - 1)}
                type="button"
              >
                <ArrowLeft aria-hidden="true" size={17} />
                Back
              </button>
            ) : (
              <span className="profile-step-counter">
                {activeStep + 1} of {steps.length}
              </span>
            )}
            {activeStep < steps.length - 1 ? (
              <button
                className="button button--primary profile-next-button"
                onClick={goToNextStep}
                type="button"
              >
                Continue
                <ArrowRight aria-hidden="true" size={17} />
              </button>
            ) : (
              <button
                className="button button--primary profile-next-button"
                disabled={saving}
                type="submit"
              >
                {saving ? "Saving profile…" : "Save and complete"}
                {!saving && <CheckCircle2 aria-hidden="true" size={17} />}
              </button>
            )}
          </div>
        </form>
      </div>
    </section>
  );
}
