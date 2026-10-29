import { apiRequest } from "./api";
import type { GovernmentJob } from "./jobs";

export interface AdminJobInput {
  slug: string;
  title: string;
  recruiting_body: string;
  description: string;
  employment_type: string | null;
  eligible_states: string[];
  minimum_qualification: string | null;
  minimum_education_level: GovernmentJob["minimum_education_level"];
  field_of_study: string | null;
  minimum_experience_years: number | null;
  minimum_age: number | null;
  maximum_age: number | null;
  keywords: string[];
  application_opens: string | null;
  application_deadline: string | null;
  deadline_status: GovernmentJob["deadline_status"];
  official_notice_url: string;
  application_url: string | null;
  status: GovernmentJob["status"];
  documents: {
    name: string;
    description: string | null;
    is_required: boolean;
  }[];
  reason: string;
}

export interface AdminDashboardData {
  administrator: { id: number; name: string };
  counts: Record<string, number>;
  categories: {
    id: number;
    name: string;
    slug: string;
    description: string | null;
    scheme_count: number;
  }[];
  schemes: {
    id: number;
    slug: string;
    name: string;
    description: string;
    benefits: string | null;
    department: string | null;
    government_level: string;
    beneficiaries: string[];
    keywords: string[];
    application_instructions: string | null;
    status: string;
    verification_status: string;
    requires_human_review: boolean;
    reviewed_by_user_id: number | null;
    last_verified_at: string | null;
    official_application_url: string | null;
    category_names: string[];
    issue_flags: string[];
    source_count: number;
    rule_count: number;
    document_count: number;
    eligibility_rules: {
      id: number;
      rule_type: string;
      rule_text: string;
      rule_data: Record<string, unknown> | null;
      source_id: number | null;
      required: boolean;
    }[];
    documents: {
      id: number;
      name: string;
      description: string | null;
      required: boolean;
    }[];
    deadlines: {
      id: number;
      status: string;
      closes_at: string | null;
      source_id: number | null;
      last_verified_at: string | null;
    }[];
  }[];
  sources: {
    id: number;
    scheme_id: string;
    scheme_name: string;
    url: string;
    title: string | null;
    domain: string | null;
    status: string;
    last_verified_at: string | null;
    reviewed_by_user_id: number | null;
    current: boolean;
    indexed_chunks: number;
  }[];
  ingestion: {
    id: number;
    scheme_id: string;
    scheme_name: string;
    url: string;
    status: string;
    indexed_chunks: number;
    indexed: boolean;
    latest_failure: string | null;
    has_failure: boolean;
  }[];
  failed_extractions: {
    id: number;
    source_id: string | null;
    created_at: string;
    error: string | null;
    scheme_id: number | null;
  }[];
  corrections: {
    id: number;
    scheme_id: number | null;
    report_type: string;
    description: string;
    status: string;
    created_at: string;
    review_notes: string | null;
  }[];
  assistant_feedback: {
    message_id: number;
    conversation_id: number;
    content: string;
    feedback: string;
    created_at: string;
  }[];
  audit_logs: {
    id: number;
    actor_user_id: number | null;
    action: string;
    entity_type: string;
    entity_id: string | null;
    details: Record<string, unknown> | null;
    created_at: string;
  }[];
  review_history: {
    id: number;
    scheme_id: number | null;
    actor_user_id: number;
    action: string;
    reason: string;
    before_snapshot: Record<string, unknown> | null;
    after_snapshot: Record<string, unknown> | null;
    created_at: string;
  }[];
}

export interface AdminSchemeUpdateInput {
  description?: string;
  benefits?: string | null;
  department?: string | null;
  government_level?: "Central" | "State" | "Local" | "Unknown";
  beneficiaries?: string[];
  keywords?: string[];
  application_instructions?: string | null;
  official_application_url?: string | null;
  status?: "active" | "inactive" | "unknown";
  reason: string;
}

export const adminService = {
  dashboard: () => apiRequest<AdminDashboardData>("/api/v1/admin/dashboard"),
  listJobs: () => apiRequest<GovernmentJob[]>("/api/v1/admin/jobs"),
  createJob: (input: AdminJobInput) =>
    apiRequest<GovernmentJob>("/api/v1/admin/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  updateJob: (slug: string, input: AdminJobInput) =>
    apiRequest<GovernmentJob>(
      `/api/v1/admin/jobs/${encodeURIComponent(slug)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      },
    ),
  verifyJob: (slug: string, reviewNote: string) =>
    apiRequest<GovernmentJob>(
      `/api/v1/admin/jobs/${encodeURIComponent(slug)}/verify`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ review_note: reviewNote }),
      },
    ),
  createScheme: (input: {
    name: string;
    slug: string;
    description: string;
    category_id: number | null;
    government_level: "Central" | "State" | "Local" | "Unknown";
  }) =>
    apiRequest<Record<string, unknown>>("/api/v1/admin/schemes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  verifyScheme: (slug: string, reviewNote: string) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/admin/schemes/${encodeURIComponent(slug)}/verify`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ review_note: reviewNote }),
      },
    ),
  updateScheme: (slug: string, input: AdminSchemeUpdateInput) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/admin/schemes/${encodeURIComponent(slug)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      },
    ),
  createCategory: (input: {
    name: string;
    slug: string;
    description: string | null;
  }) =>
    apiRequest<Record<string, unknown>>("/api/v1/admin/categories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  updateCategory: (
    categoryId: number,
    input: { name: string; slug: string; description: string | null },
  ) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/admin/categories/${categoryId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      },
    ),
  deleteCategory: (categoryId: number) =>
    apiRequest<void>(`/api/v1/admin/categories/${categoryId}`, {
      method: "DELETE",
    }),
  verifySource: (sourceId: number, verificationNote: string) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/admin/sources/${sourceId}/verify`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verification_note: verificationNote }),
      },
    ),
  recordSourceReview: (sourceId: number, verificationNote: string) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/admin/sources/${sourceId}/review`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verification_note: verificationNote }),
      },
    ),
  markSourceStale: (sourceId: number) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/admin/sources/${sourceId}/mark-stale`,
      { method: "POST" },
    ),
  createSource: (
    schemeSlug: string,
    input: {
      url: string;
      title: string;
      source_type:
        "official_portal" | "government_document" | "department_page" | "other";
    },
  ) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/admin/schemes/${encodeURIComponent(schemeSlug)}/sources`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      },
    ),
  createEligibilityRule: (
    schemeSlug: string,
    input: {
      rule_type: string;
      rule_text: string;
      rule_data: Record<string, unknown> | null;
      source_id: number | null;
      is_required: boolean;
      reason: string;
    },
  ) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/admin/schemes/${encodeURIComponent(schemeSlug)}/eligibility-rules`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      },
    ),
  createDocumentRequirement: (
    schemeSlug: string,
    input: {
      name: string;
      description: string | null;
      is_required: boolean;
      reason: string;
    },
  ) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/admin/schemes/${encodeURIComponent(schemeSlug)}/documents`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      },
    ),
  createDeadline: (
    schemeSlug: string,
    input: {
      deadline_type: string;
      deadline_status: "known" | "unknown";
      closes_at: string | null;
      source_id: number | null;
      notes: string | null;
    },
  ) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/admin/schemes/${encodeURIComponent(schemeSlug)}/deadlines`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      },
    ),
  reindexSource: (sourceId: number) => {
    const form = new FormData();
    form.set("source_id", String(sourceId));
    return apiRequest<Record<string, unknown>>(
      "/api/v1/admin/knowledge/ingest",
      { method: "POST", body: form },
    );
  },
  reviewCorrection: (
    reportId: number,
    status: "in_review" | "resolved" | "declined",
    review_notes: string,
  ) =>
    apiRequest<Record<string, unknown>>(
      `/api/v1/admin/scheme-corrections/${reportId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, review_notes }),
      },
    ),
};
