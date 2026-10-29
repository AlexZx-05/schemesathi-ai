import { apiRequest } from "./api";

export interface GovernmentJobDocument {
  id: number;
  name: string;
  description: string | null;
  is_required: boolean;
}

export interface GovernmentJob {
  id: number;
  slug: string;
  title: string;
  recruiting_body: string;
  description: string;
  employment_type: string | null;
  eligible_states: string[];
  minimum_qualification: string | null;
  minimum_education_level: string | null;
  field_of_study: string | null;
  minimum_experience_years: number | null;
  minimum_age: number | null;
  maximum_age: number | null;
  keywords: string[];
  application_opens: string | null;
  application_deadline: string | null;
  deadline_status: "known" | "unknown";
  official_notice_url: string;
  application_url: string | null;
  status: "upcoming" | "open" | "closed" | "unknown";
  verification_status: "unverified" | "verified" | "requires_review";
  last_verified_at: string | null;
  documents: GovernmentJobDocument[];
}

export interface JobRecommendation extends GovernmentJob {
  match_reasons: string[];
  missing_information: string[];
}

export interface GovernmentJobPage {
  items: GovernmentJob[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface JobRecommendationPage {
  items: JobRecommendation[];
  profile_complete: boolean;
}

export const jobService = {
  listJobs: (query = "") => {
    const params = new URLSearchParams({ page_size: "50" });
    if (query.trim()) params.set("q", query.trim());
    return apiRequest<GovernmentJobPage>(`/api/v1/jobs?${params.toString()}`);
  },
  getJob: (slug: string) =>
    apiRequest<GovernmentJob>(`/api/v1/jobs/${encodeURIComponent(slug)}`),
  getRecommendations: () =>
    apiRequest<JobRecommendationPage>("/api/v1/job-recommendations"),
};
