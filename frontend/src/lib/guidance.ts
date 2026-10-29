import { apiRequest } from "./api";

export type ApplicationStatus =
  | "planning"
  | "preparing_documents"
  | "ready_to_apply"
  | "submitted_externally"
  | "in_progress"
  | "completed"
  | "not_proceeding";

export interface SavedScheme {
  id: number;
  scheme_id: string;
  scheme_name: string;
  scheme_status: string;
  verification_status: string;
  last_verified_at: string | null;
  guidance_available: boolean;
  availability_notice: string | null;
  saved_at: string;
}

export interface DocumentChecklistItem {
  document_id: number;
  name: string;
  description: string | null;
  is_required: boolean;
  ready: boolean;
  ready_at: string | null;
  uncertainty_notice: string | null;
}

export interface DocumentChecklist {
  scheme_id: string;
  scheme_name: string;
  verification_status: string;
  last_verified_at: string | null;
  source_urls: string[];
  items: DocumentChecklistItem[];
  notice: string;
}

export interface ApplicationGuidance {
  scheme_id: string;
  scheme_name: string;
  application_steps: string[];
  official_application_url: string | null;
  source_urls: string[];
  checklist_complete: boolean;
  checklist_required_remaining: number;
  portal_notice: string;
  submission_notice: string;
}

export interface ApplicationTracking {
  id: number;
  scheme_id: string;
  scheme_name: string;
  status: ApplicationStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
  status_changed_at: string;
  submitted_at: string | null;
  submitted_by_user_confirmation: boolean;
  progress_percent: number;
}

export const guidanceService = {
  listSaved: () => apiRequest<SavedScheme[]>("/api/v1/saved-schemes"),
  save: (schemeId: string) =>
    apiRequest<SavedScheme>(`/api/v1/saved-schemes/${encodeURIComponent(schemeId)}`, { method: "POST" }),
  unsave: (schemeId: string) =>
    apiRequest<void>(`/api/v1/saved-schemes/${encodeURIComponent(schemeId)}`, { method: "DELETE" }),
  getChecklist: (schemeId: string) =>
    apiRequest<DocumentChecklist>(`/api/v1/schemes/${encodeURIComponent(schemeId)}/documents/checklist`),
  setDocumentReady: (schemeId: string, documentId: number, ready: boolean) =>
    apiRequest<DocumentChecklistItem>(
      `/api/v1/schemes/${encodeURIComponent(schemeId)}/documents/${documentId}`,
      { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ready }) },
    ),
  getApplicationGuidance: (schemeId: string) =>
    apiRequest<ApplicationGuidance>(`/api/v1/schemes/${encodeURIComponent(schemeId)}/application-guidance`),
  createApplication: (schemeId: string, notes?: string) =>
    apiRequest<ApplicationTracking>("/api/v1/applications", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scheme_id: schemeId, notes: notes || null }),
    }),
  listApplications: (status?: ApplicationStatus) =>
    apiRequest<ApplicationTracking[]>(`/api/v1/applications${status ? `?status=${status}` : ""}`),
  getApplication: (applicationId: number) =>
    apiRequest<ApplicationTracking>(`/api/v1/applications/${applicationId}`),
  updateApplication: (
    applicationId: number,
    input: { status: ApplicationStatus; notes?: string; confirm_external_submission?: boolean },
  ) => apiRequest<ApplicationTracking>(`/api/v1/applications/${applicationId}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
  }),
};
