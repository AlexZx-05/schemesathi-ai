import { ApiError, apiRequest } from "../api";
import {
  beneficiaryGroups,
  schemeCategories,
  type BeneficiaryGroup,
  type GovernmentLevel,
  type Scheme,
} from "./types";

interface SchemeApiRecord {
  id: string;
  name: string;
  short_description: string;
  category: string | null;
  beneficiaries: string[];
  government_level: string;
  keywords: string[];
  benefits: string[];
  eligibility_criteria: string[];
  required_documents: string[];
  application_procedure: string[];
  official_source: string | null;
  last_verified_date: string | null;
  data_status: Scheme["dataStatus"];
  sources?: {
    url: string;
    title: string | null;
    status: NonNullable<Scheme["sources"]>[number]["status"];
    last_verified_at: string | null;
  }[];
}

interface SchemePage {
  items: SchemeApiRecord[];
}

export interface EligibilityCriterion {
  rule_id: number;
  criterion: string;
  profile_field: string | null;
  result: "satisfied" | "not_satisfied" | "unknown" | "requires_confirmation";
  explanation: string;
  required: boolean;
  evaluated_value: string | number | boolean | string[] | null;
  rule_source_references: EligibilityAssessmentSource[];
  uncertainty_reason: string | null;
}

export interface EligibilityAssessmentSource {
  title: string | null;
  url: string;
  last_verified_at: string | null;
}

export interface EligibilityAssessment {
  scheme_id: string;
  scheme_name: string;
  outcome:
    | "potentially_eligible"
    | "more_information_required"
    | "known_criteria_not_satisfied"
    | "unable_to_determine";
  summary: string;
  criteria: EligibilityCriterion[];
  sources: EligibilityAssessmentSource[];
  assessed_at: string;
  disclaimer: string;
  assessment_mode: "saved_profile" | "hypothetical_answers";
  missing_information: string[];
}

export interface EligibilityHypotheticalAnswers {
  age?: number | null;
  state?: string | null;
  district?: string | null;
  area_type?: "Rural" | "Urban" | null;
  occupation?:
    | "Student"
    | "Farmer"
    | "Salaried employee"
    | "Self-employed"
    | "Job seeker"
    | "Homemaker"
    | "Other"
    | null;
  employment_status?:
    | "Employed"
    | "Self-employed"
    | "Unemployed"
    | "Student"
    | "Homemaker"
    | "Other"
    | null;
  worker_category?: string | null;
  education_level?:
    | "No formal schooling"
    | "Primary"
    | "Secondary"
    | "Higher secondary"
    | "Diploma or vocational"
    | "Undergraduate"
    | "Postgraduate"
    | "Other"
    | null;
  current_student?: boolean | null;
  annual_income_range?:
    | "Prefer not to say"
    | "Below ₹1 lakh"
    | "₹1–3 lakh"
    | "₹3–6 lakh"
    | "₹6–10 lakh"
    | "Above ₹10 lakh"
    | null;
  household_size?: number | null;
  beneficiary_categories?: string[];
}

export interface SchemeRecommendation {
  scheme_id: string;
  scheme_name: string;
  short_description: string;
  category: string | null;
  data_status: Scheme["dataStatus"];
  eligibility_status: EligibilityAssessment["outcome"];
  summary: string;
  reasons: string[];
  criteria: EligibilityCriterion[];
  missing_information: string[];
  sources: EligibilityAssessment["sources"];
}

export interface RecommendationPage {
  profile_complete: boolean;
  completion_percentage: number;
  missing_profile_fields: string[];
  items: SchemeRecommendation[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface DashboardSummary {
  application_total: number;
  application_status_counts: Record<string, number>;
  verified_upcoming_deadlines: {
    scheme_id: string;
    scheme_name: string;
    closes_at: string;
    source_title: string | null;
    source_url: string;
  }[];
}

function toScheme(record: SchemeApiRecord): Scheme {
  const category = record.category
    ? schemeCategories.find((item) => item === record.category)
    : null;
  const levels: readonly GovernmentLevel[] = [
    "Central",
    "State",
    "Local",
    "Unknown",
  ];
  const governmentLevel = levels.find(
    (item) => item === record.government_level,
  );
  if ((record.category && !category) || !governmentLevel) {
    throw new Error(
      `Scheme "${record.id}" contains an unsupported category or government level.`,
    );
  }

  const beneficiaries: BeneficiaryGroup[] = record.beneficiaries.map(
    (value) => {
      const group = beneficiaryGroups.find((item) => item === value);
      if (!group) {
        throw new Error(
          `Scheme "${record.id}" contains an unsupported beneficiary group.`,
        );
      }
      return group;
    },
  );

  return {
    id: record.id,
    name: record.name,
    shortDescription: record.short_description,
    category: category ?? null,
    beneficiaries,
    governmentLevel,
    keywords: record.keywords,
    benefits: record.benefits,
    eligibilityCriteria: record.eligibility_criteria,
    requiredDocuments: record.required_documents,
    applicationProcedure: record.application_procedure,
    officialSource: record.official_source,
    lastVerifiedDate: record.last_verified_date,
    dataStatus: record.data_status,
    sources:
      record.sources?.map((source) => ({
        url: source.url,
        title: source.title,
        status: source.status,
        lastVerifiedAt: source.last_verified_at,
      })) ?? [],
  };
}

export interface SchemeService {
  getSchemes(): Promise<Scheme[]>;
  getSchemeById(schemeId: string): Promise<Scheme | null>;
  assessEligibility(
    schemeId: string,
    answers?: EligibilityHypotheticalAnswers,
  ): Promise<EligibilityAssessment>;
  getRecommendations(page?: number, pageSize?: number): Promise<RecommendationPage>;
  getDashboardSummary(): Promise<DashboardSummary>;
}

export const schemeService: SchemeService = {
  async getSchemes() {
    const page = await apiRequest<SchemePage>("/api/v1/schemes?page_size=100");
    return page.items.map(toScheme);
  },

  async getSchemeById(schemeId) {
    try {
      const record = await apiRequest<SchemeApiRecord>(
        `/api/v1/schemes/${encodeURIComponent(schemeId)}`,
      );
      return toScheme(record);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  },

  assessEligibility: (schemeId, answers) =>
    apiRequest<EligibilityAssessment>(
      `/api/v1/schemes/${encodeURIComponent(schemeId)}/eligibility-check`,
      {
        method: "POST",
        ...(answers
          ? {
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ answers }),
            }
          : {}),
      },
    ),
  getRecommendations: (page = 1, pageSize = 6) =>
    apiRequest<RecommendationPage>(
      `/api/v1/recommendations?page=${page}&page_size=${pageSize}`,
    ),
  getDashboardSummary: () =>
    apiRequest<DashboardSummary>("/api/v1/dashboard/summary"),
};
