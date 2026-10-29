import {
  AlertTriangle,
  Check,
  ClipboardList,
  Database,
  FileWarning,
  History,
  Layers3,
  RefreshCw,
  ShieldCheck,
  ThumbsDown,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "../context/AuthContext";
import {
  adminService,
  type AdminDashboardData,
  type AdminSchemeUpdateInput,
} from "../lib/admin";

type Section =
  | "overview"
  | "schemes"
  | "categories"
  | "sources"
  | "rag"
  | "corrections"
  | "feedback"
  | "audit"
  | "reviews";

const sections: { id: Section; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "schemes", label: "Schemes & quality" },
  { id: "categories", label: "Categories" },
  { id: "sources", label: "Official sources" },
  { id: "rag", label: "RAG documents" },
  { id: "corrections", label: "User corrections" },
  { id: "feedback", label: "AI feedback" },
  { id: "reviews", label: "Review history" },
  { id: "audit", label: "Audit logs" },
];

function dateLabel(value: string | null) {
  return value
    ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
        new Date(value),
      )
    : "Not recorded";
}

function governmentLevel(
  value: string,
): "Central" | "State" | "Local" | "Unknown" {
  switch (value) {
    case "Central":
    case "State":
    case "Local":
      return value;
    default:
      return "Unknown";
  }
}

function schemeStatus(value: string): "active" | "inactive" | "unknown" {
  switch (value) {
    case "active":
    case "inactive":
      return value;
    default:
      return "unknown";
  }
}

function formLines(value: FormDataEntryValue | null): string[] {
  return String(value ?? "")
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function sourceType(
  value: string,
): "official_portal" | "government_document" | "department_page" | "other" {
  switch (value) {
    case "government_document":
    case "department_page":
    case "other":
      return value;
    default:
      return "official_portal";
  }
}

function AdminState({ message }: { message: string }) {
  return (
    <div className="admin-state" role="alert">
      <AlertTriangle aria-hidden="true" size={20} />
      <p>{message}</p>
    </div>
  );
}

export function AdminDashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<AdminDashboardData | null>(null);
  const [section, setSection] = useState<Section>("overview");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await adminService.dashboard());
      setError(null);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not load administrator data.",
      );
    }
  }, []);

  useEffect(() => {
    if (user?.is_admin) void load();
  }, [load, user?.is_admin]);

  async function action(key: string, operation: () => Promise<unknown>) {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await operation();
      setNotice(
        "Administrator change saved and recorded in the review history.",
      );
      await load();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "The administrator action could not be completed.",
      );
    } finally {
      setBusy(null);
    }
  }

  if (!user?.is_admin) {
    return (
      <section className="admin-page">
        <AdminState message="Administrator access is required. This page is protected by server-side role checks as well." />
      </section>
    );
  }

  return (
    <section aria-labelledby="admin-title" className="admin-page">
      <header className="admin-header">
        <div>
          <p className="eyebrow">Restricted workspace</p>
          <h1 id="admin-title">Scheme data administration</h1>
          <p>
            Review source freshness, correct catalogue data, and keep a
            traceable history of administrator decisions.
          </p>
        </div>
        <button
          className="button button--secondary"
          disabled={busy !== null}
          onClick={() => void load()}
          type="button"
        >
          <RefreshCw aria-hidden="true" size={16} />
          Refresh data
        </button>
      </header>
      <nav aria-label="Admin sections" className="admin-tabs">
        {sections.map((item) => (
          <button
            aria-current={section === item.id ? "page" : undefined}
            className={
              section === item.id ? "admin-tab admin-tab--active" : "admin-tab"
            }
            key={item.id}
            onClick={() => setSection(item.id)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </nav>
      {error && <AdminState message={error} />}
      {notice && (
        <p className="admin-success" role="status">
          {notice}
        </p>
      )}
      {!data && !error && (
        <div aria-live="polite" className="guidance-state">
          Loading protected administration data…
        </div>
      )}
      {data && section === "overview" && <Overview data={data} />}
      {data && section === "schemes" && (
        <Schemes
          busy={busy}
          data={data}
          onCreate={(input) =>
            void action("scheme-create", () => adminService.createScheme(input))
          }
          onAddRule={(slug, input) =>
            void action(`rule-create-${slug}`, () =>
              adminService.createEligibilityRule(slug, input),
            )
          }
          onAddDocument={(slug, input) =>
            void action(`document-create-${slug}`, () =>
              adminService.createDocumentRequirement(slug, input),
            )
          }
          onAddDeadline={(slug, input) =>
            void action(`deadline-create-${slug}`, () =>
              adminService.createDeadline(slug, input),
            )
          }
          onUpdateScheme={(slug, input) =>
            void action(`scheme-edit-${slug}`, () =>
              adminService.updateScheme(slug, input),
            )
          }
          onVerify={(scheme) => {
            const note = window.prompt(
              `Review ${scheme.name} against its official sources. Enter a review note:`,
            );
            if (note && note.trim().length >= 10) {
              void action(`scheme-${scheme.slug}`, () =>
                adminService.verifyScheme(scheme.slug, note.trim()),
              );
            }
          }}
        />
      )}
      {data && section === "categories" && (
        <Categories
          busy={busy}
          data={data}
          onCreate={(input) =>
            void action("category-create", () =>
              adminService.createCategory(input),
            )
          }
          onUpdate={(category) => {
            const name = window.prompt("Category name:", category.name);
            if (name === null) return;
            const slug = window.prompt("Category slug:", category.slug);
            if (slug === null) return;
            const description = window.prompt(
              "Description (optional):",
              category.description || "",
            );
            if (description !== null) {
              void action(`category-${category.id}`, () =>
                adminService.updateCategory(category.id, {
                  name: name.trim(),
                  slug: slug.trim(),
                  description: description.trim() || null,
                }),
              );
            }
          }}
          onDelete={(categoryId) => {
            if (
              window.confirm(
                "Delete this category? Categories with assigned schemes cannot be deleted.",
              )
            ) {
              void action(`category-delete-${categoryId}`, () =>
                adminService.deleteCategory(categoryId),
              );
            }
          }}
        />
      )}
      {data && section === "sources" && (
        <Sources
          busy={busy}
          data={data}
          onCreate={(schemeSlug, input) =>
            void action(`source-create-${schemeSlug}`, () =>
              adminService.createSource(schemeSlug, input),
            )
          }
          onMarkStale={(sourceId) => {
            if (window.confirm("Mark this source stale and disable its use?")) {
              void action(`source-stale-${sourceId}`, () =>
                adminService.markSourceStale(sourceId),
              );
            }
          }}
          onVerify={(source) => {
            const note = window.prompt(
              `Review ${source.url} and enter a verification note:`,
            );
            if (note && note.trim().length >= 10) {
              void action(`source-${source.id}`, async () => {
                await adminService.verifySource(source.id, note.trim());
                await adminService.recordSourceReview(source.id, note.trim());
              });
            }
          }}
        />
      )}
      {data && section === "rag" && (
        <Rag
          busy={busy}
          data={data}
          onReindex={(sourceId) =>
            void action(`reindex-${sourceId}`, () =>
              adminService.reindexSource(sourceId),
            )
          }
        />
      )}
      {data && section === "corrections" && (
        <Corrections
          busy={busy}
          data={data}
          onReview={(reportId, status) => {
            const note = window.prompt(
              "Add a review note (at least 5 characters):",
            );
            if (note && note.trim().length >= 5) {
              void action(`correction-${reportId}`, () =>
                adminService.reviewCorrection(reportId, status, note.trim()),
              );
            }
          }}
        />
      )}
      {data && section === "feedback" && <Feedback data={data} />}
      {data && section === "audit" && <Audit data={data} />}
      {data && section === "reviews" && <Reviews data={data} />}
    </section>
  );
}

function Overview({ data }: { data: AdminDashboardData }) {
  const cards = [
    ["Schemes", data.counts.schemes, Layers3],
    ["Verified schemes", data.counts.verified_schemes, ShieldCheck],
    ["Stale sources", data.counts.stale_sources, AlertTriangle],
    ["Indexed sources", data.counts.indexed_documents, Database],
    ["Failed extractions", data.counts.failed_extractions, FileWarning],
    ["Open corrections", data.counts.open_corrections, ClipboardList],
    ["AI feedback", data.counts.feedback_items, ThumbsDown],
  ] as const;
  return (
    <div className="admin-overview">
      <div className="admin-metric-grid">
        {cards.map(([label, value, Icon]) => (
          <article className="admin-metric" key={label}>
            <Icon aria-hidden="true" size={19} />
            <span>{label}</span>
            <strong>{value ?? 0}</strong>
          </article>
        ))}
      </div>
      <div className="admin-panel">
        <h2>Needs attention</h2>
        {data.schemes.filter((scheme) => scheme.issue_flags.length > 0)
          .length ? (
          <ul className="admin-attention-list">
            {data.schemes
              .filter((scheme) => scheme.issue_flags.length > 0)
              .map((scheme) => (
                <li key={scheme.id}>
                  <strong>{scheme.name}</strong>
                  <span>{scheme.issue_flags.join(" · ")}</span>
                </li>
              ))}
          </ul>
        ) : (
          <p>No catalogue quality flags are currently recorded.</p>
        )}
      </div>
    </div>
  );
}

function Schemes({
  data,
  busy,
  onCreate,
  onAddRule,
  onAddDocument,
  onAddDeadline,
  onUpdateScheme,
  onVerify,
}: {
  data: AdminDashboardData;
  busy: string | null;
  onCreate: (input: {
    name: string;
    slug: string;
    description: string;
    category_id: number | null;
    government_level: "Central" | "State" | "Local" | "Unknown";
  }) => void;
  onAddRule: (
    slug: string,
    input: {
      rule_type: string;
      rule_text: string;
      rule_data: Record<string, unknown> | null;
      source_id: number | null;
      is_required: boolean;
      reason: string;
    },
  ) => void;
  onAddDocument: (
    slug: string,
    input: {
      name: string;
      description: string | null;
      is_required: boolean;
      reason: string;
    },
  ) => void;
  onAddDeadline: (
    slug: string,
    input: {
      deadline_type: string;
      deadline_status: "known" | "unknown";
      closes_at: string | null;
      source_id: number | null;
      notes: string | null;
    },
  ) => void;
  onUpdateScheme: (slug: string, input: AdminSchemeUpdateInput) => void;
  onVerify: (scheme: AdminDashboardData["schemes"][number]) => void;
}) {
  return (
    <div className="admin-record-list">
      <form
        className="admin-category-form"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          const category = String(form.get("category_id"));
          onCreate({
            name: String(form.get("name")).trim(),
            slug: String(form.get("slug")).trim(),
            description: String(form.get("description")).trim(),
            category_id: category ? Number(category) : null,
            government_level: governmentLevel(
              String(form.get("government_level")),
            ),
          });
          event.currentTarget.reset();
        }}
      >
        <label>
          Scheme name
          <input maxLength={200} minLength={2} name="name" required />
        </label>
        <label>
          Slug
          <input
            maxLength={220}
            minLength={2}
            name="slug"
            pattern="[a-z0-9]+(-[a-z0-9]+)*"
            required
          />
        </label>
        <label>
          Description
          <input maxLength={12000} minLength={10} name="description" required />
        </label>
        <label>
          Category
          <select defaultValue="" name="category_id">
            <option value="">No category</option>
            {data.categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Government level
          <select defaultValue="Unknown" name="government_level">
            {["Central", "State", "Local", "Unknown"].map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </label>
        <button className="button button--primary" disabled={busy !== null}>
          Add unverified scheme
        </button>
      </form>
      {data.schemes.map((scheme) => (
        <article className="admin-record" key={scheme.id}>
          <div className="admin-record-main">
            <h2>{scheme.name}</h2>
            <p>
              {scheme.slug} · {scheme.status} · {scheme.verification_status}
            </p>
            <p>
              {scheme.category_names.join(", ") || "Uncategorized"} ·{" "}
              {scheme.source_count} sources · {scheme.rule_count} rules ·{" "}
              {scheme.document_count} documents
            </p>
            {scheme.issue_flags.map((flag) => (
              <span className="admin-flag" key={flag}>
                {flag}
              </span>
            ))}
            <p>
              Reviewed {dateLabel(scheme.last_verified_at)} · reviewer ID{" "}
              {scheme.reviewed_by_user_id ?? "not recorded"}
            </p>
            <details className="admin-detail">
              <summary>Review rules, documents, and deadlines</summary>
              <h3>Eligibility rules</h3>
              {scheme.eligibility_rules.length ? (
                <ul>
                  {scheme.eligibility_rules.map((rule) => (
                    <li key={rule.id}>
                      {rule.rule_text} · source {rule.source_id ?? "not linked"}{" "}
                      · {rule.rule_data ? "structured" : "unstructured"}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No eligibility rules.</p>
              )}
              <h3>Document requirements</h3>
              {scheme.documents.length ? (
                <ul>
                  {scheme.documents.map((document) => (
                    <li key={document.id}>
                      {document.name} ·{" "}
                      {document.required ? "required" : "optional"}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No document requirements.</p>
              )}
              <h3>Deadlines</h3>
              {scheme.deadlines.length ? (
                <ul>
                  {scheme.deadlines.map((deadline) => (
                    <li key={deadline.id}>
                      {deadline.status} · {dateLabel(deadline.closes_at)} ·
                      source {deadline.source_id ?? "not linked"} · verified{" "}
                      {dateLabel(deadline.last_verified_at)}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No deadline recorded; unknown remains unknown.</p>
              )}
            </details>
          </div>
          {scheme.verification_status !== "verified" && (
            <button
              className="button button--secondary"
              disabled={busy !== null}
              onClick={() => onVerify(scheme)}
              type="button"
            >
              <ShieldCheck aria-hidden="true" size={15} />
              Verify record
            </button>
          )}
          <details className="admin-detail">
            <summary>Edit scheme information</summary>
            <form
              className="admin-inline-form"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                const benefits = String(form.get("benefits")).trim();
                const instructions = String(
                  form.get("application_instructions"),
                ).trim();
                const department = String(form.get("department")).trim();
                const applicationUrl = String(
                  form.get("official_application_url"),
                ).trim();
                onUpdateScheme(scheme.slug, {
                  description: String(form.get("description")).trim(),
                  benefits: benefits || null,
                  department: department || null,
                  government_level: governmentLevel(
                    String(form.get("government_level")),
                  ),
                  beneficiaries: formLines(form.get("beneficiaries")),
                  keywords: formLines(form.get("keywords")),
                  application_instructions: instructions || null,
                  official_application_url: applicationUrl || null,
                  status: schemeStatus(String(form.get("status"))),
                  reason: String(form.get("reason")).trim(),
                });
              }}
            >
              <label>
                Source-backed overview
                <textarea
                  maxLength={12000}
                  minLength={10}
                  name="description"
                  required
                  rows={3}
                  defaultValue={scheme.description}
                />
              </label>
              <label>
                Benefits (one per line)
                <textarea
                  maxLength={12000}
                  name="benefits"
                  rows={3}
                  defaultValue={scheme.benefits ?? ""}
                />
              </label>
              <label>
                Department
                <input
                  maxLength={200}
                  name="department"
                  defaultValue={scheme.department ?? ""}
                />
              </label>
              <label>
                Beneficiary groups (one per line)
                <textarea
                  name="beneficiaries"
                  rows={2}
                  defaultValue={scheme.beneficiaries.join("\n")}
                />
              </label>
              <label>
                Search keywords (one per line)
                <textarea
                  name="keywords"
                  rows={2}
                  defaultValue={scheme.keywords.join("\n")}
                />
              </label>
              <label>
                Application steps (one per line)
                <textarea
                  maxLength={12000}
                  name="application_instructions"
                  rows={3}
                  defaultValue={scheme.application_instructions ?? ""}
                />
              </label>
              <label>
                Official application URL
                <input
                  name="official_application_url"
                  type="url"
                  defaultValue={scheme.official_application_url ?? ""}
                />
              </label>
              <label>
                Scheme status
                <select name="status" defaultValue={scheme.status}>
                  <option value="unknown">Unknown</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </label>
              <label>
                Change reason
                <input
                  maxLength={2000}
                  minLength={10}
                  name="reason"
                  required
                />
              </label>
              <button
                className="button button--secondary"
                disabled={busy !== null}
              >
                Save scheme information
              </button>
            </form>
          </details>
          <details className="admin-detail">
            <summary>Add reviewed data</summary>
            <form
              className="admin-inline-form"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                const json = String(form.get("rule_data")).trim();
                let ruleData: Record<string, unknown> | null = null;
                if (json) {
                  try {
                    const parsed: unknown = JSON.parse(json);
                    if (
                      parsed === null ||
                      typeof parsed !== "object" ||
                      Array.isArray(parsed)
                    ) {
                      window.alert(
                        "Eligibility rule data must be a JSON object.",
                      );
                      return;
                    }
                    ruleData = Object.fromEntries(Object.entries(parsed));
                  } catch {
                    window.alert(
                      "Enter valid JSON for the structured rule, or leave it blank.",
                    );
                    return;
                  }
                }
                const rawSourceId = String(form.get("source_id"));
                onAddRule(scheme.slug, {
                  rule_type: String(form.get("rule_type")).trim(),
                  rule_text: String(form.get("rule_text")).trim(),
                  rule_data: ruleData,
                  source_id: rawSourceId ? Number(rawSourceId) : null,
                  is_required: true,
                  reason: String(form.get("reason")).trim(),
                });
                event.currentTarget.reset();
              }}
            >
              <h3>Eligibility rule</h3>
              <label>
                Rule type
                <input maxLength={40} minLength={1} name="rule_type" required />
              </label>
              <label>
                Requirement
                <input
                  maxLength={2000}
                  minLength={3}
                  name="rule_text"
                  required
                />
              </label>
              <label>
                Source
                <select defaultValue="" name="source_id">
                  <option value="">Source not yet linked</option>
                  {data.sources
                    .filter((source) => source.scheme_id === scheme.slug)
                    .map((source) => (
                      <option key={source.id} value={source.id}>
                        {source.title || source.url}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Structured rule JSON (optional)
                <input
                  aria-describedby={`rule-json-help-${scheme.id}`}
                  name="rule_data"
                  placeholder='{"field":"state","operator":"equals","value":"..."}'
                />
              </label>
              <p id={`rule-json-help-${scheme.id}`}>
                Unsupported or unlinked criteria remain flagged for independent
                review and are not treated as verified.
              </p>
              <label>
                Review reason
                <input maxLength={2000} minLength={10} name="reason" required />
              </label>
              <button
                className="button button--secondary"
                disabled={busy !== null}
              >
                Add eligibility rule
              </button>
            </form>
            <form
              className="admin-inline-form"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                onAddDocument(scheme.slug, {
                  name: String(form.get("document_name")).trim(),
                  description:
                    String(form.get("document_description")).trim() || null,
                  is_required: true,
                  reason: String(form.get("document_reason")).trim(),
                });
                event.currentTarget.reset();
              }}
            >
              <h3>Document requirement</h3>
              <label>
                Document name
                <input
                  maxLength={200}
                  minLength={2}
                  name="document_name"
                  required
                />
              </label>
              <label>
                Description or uncertainty note
                <input maxLength={2000} name="document_description" />
              </label>
              <label>
                Review reason
                <input
                  maxLength={2000}
                  minLength={10}
                  name="document_reason"
                  required
                />
              </label>
              <button
                className="button button--secondary"
                disabled={busy !== null}
              >
                Add document requirement
              </button>
            </form>
            <form
              className="admin-inline-form"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                const status = String(form.get("deadline_status")) as
                  "known" | "unknown";
                const closes = String(form.get("closes_at"));
                const source = String(form.get("deadline_source_id"));
                onAddDeadline(scheme.slug, {
                  deadline_type: "application",
                  deadline_status: status,
                  closes_at:
                    status === "known" && closes
                      ? new Date(closes).toISOString()
                      : null,
                  source_id: source ? Number(source) : null,
                  notes: String(form.get("deadline_notes")).trim() || null,
                });
                event.currentTarget.reset();
              }}
            >
              <h3>Application deadline</h3>
              <label>
                Status
                <select defaultValue="unknown" name="deadline_status">
                  <option value="unknown">Unknown</option>
                  <option value="known">Known and source-verified</option>
                </select>
              </label>
              <label>
                Closing date (required for known deadlines)
                <input name="closes_at" type="datetime-local" />
              </label>
              <label>
                Supporting source
                <select defaultValue="" name="deadline_source_id">
                  <option value="">No source linked</option>
                  {data.sources
                    .filter((source) => source.scheme_id === scheme.slug)
                    .map((source) => (
                      <option key={source.id} value={source.id}>
                        {source.title || source.url} · {source.status}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Notes
                <input maxLength={2000} name="deadline_notes" />
              </label>
              <button
                className="button button--secondary"
                disabled={busy !== null}
              >
                Record deadline
              </button>
            </form>
          </details>
        </article>
      ))}
    </div>
  );
}

function Categories({
  data,
  busy,
  onCreate,
  onUpdate,
  onDelete,
}: {
  data: AdminDashboardData;
  busy: string | null;
  onCreate: (input: {
    name: string;
    slug: string;
    description: string | null;
  }) => void;
  onUpdate: (category: AdminDashboardData["categories"][number]) => void;
  onDelete: (categoryId: number) => void;
}) {
  return (
    <div className="admin-record-list">
      <form
        className="admin-category-form"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          onCreate({
            name: String(form.get("name")).trim(),
            slug: String(form.get("slug")).trim(),
            description: String(form.get("description")).trim() || null,
          });
          event.currentTarget.reset();
        }}
      >
        <label>
          Name
          <input maxLength={100} minLength={2} name="name" required />
        </label>
        <label>
          Slug
          <input
            maxLength={120}
            minLength={2}
            name="slug"
            pattern="[a-z0-9]+(-[a-z0-9]+)*"
            required
          />
        </label>
        <label>
          Description
          <input maxLength={500} name="description" />
        </label>
        <button className="button button--primary" disabled={busy !== null}>
          Add category
        </button>
      </form>
      {data.categories.map((category) => (
        <article className="admin-record" key={category.id}>
          <div className="admin-record-main">
            <h2>{category.name}</h2>
            <p>
              {category.slug} · {category.scheme_count} associated schemes
            </p>
            {category.description && <p>{category.description}</p>}
          </div>
          <div className="admin-actions">
            <button
              className="button button--secondary"
              disabled={busy !== null}
              onClick={() => onUpdate(category)}
              type="button"
            >
              Edit
            </button>
            <button
              className="button button--quiet"
              disabled={busy !== null}
              onClick={() => onDelete(category.id)}
              type="button"
            >
              Delete
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}

function Sources({
  data,
  busy,
  onCreate,
  onVerify,
  onMarkStale,
}: {
  data: AdminDashboardData;
  busy: string | null;
  onCreate: (
    schemeSlug: string,
    input: {
      url: string;
      title: string;
      source_type:
        "official_portal" | "government_document" | "department_page" | "other";
    },
  ) => void;
  onVerify: (source: AdminDashboardData["sources"][number]) => void;
  onMarkStale: (sourceId: number) => void;
}) {
  return (
    <div className="admin-record-list">
      <form
        className="admin-category-form"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          onCreate(String(form.get("scheme_slug")), {
            url: String(form.get("source_url")).trim(),
            title: String(form.get("source_title")).trim(),
            source_type: sourceType(String(form.get("source_type"))),
          });
          event.currentTarget.reset();
        }}
      >
        <label>
          Scheme
          <select defaultValue="" name="scheme_slug" required>
            <option disabled value="">
              Select scheme
            </option>
            {data.schemes.map((scheme) => (
              <option key={scheme.id} value={scheme.slug}>
                {scheme.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Official HTTPS source URL
          <input name="source_url" required type="url" />
        </label>
        <label>
          Source title
          <input maxLength={300} minLength={1} name="source_title" required />
        </label>
        <label>
          Source type
          <select defaultValue="official_portal" name="source_type">
            <option value="official_portal">Official portal</option>
            <option value="government_document">Government document</option>
            <option value="department_page">Department page</option>
            <option value="other">Other</option>
          </select>
        </label>
        <button className="button button--primary" disabled={busy !== null}>
          Register unverified source
        </button>
      </form>
      {data.sources.map((source) => (
        <article className="admin-record" key={source.id}>
          <div className="admin-record-main">
            <h2>{source.title || source.scheme_name}</h2>
            <a href={source.url} rel="noreferrer" target="_blank">
              {source.url}
            </a>
            <p>
              {source.scheme_name} · {source.domain || "domain not recorded"} ·{" "}
              {source.status} · {source.indexed_chunks} indexed chunks
            </p>
            <p>
              Last verified {dateLabel(source.last_verified_at)} · reviewer ID{" "}
              {source.reviewed_by_user_id ?? "not recorded"} ·{" "}
              {source.current ? "current" : "needs review"}
            </p>
          </div>
          <div className="admin-actions">
            {source.status !== "verified" && (
              <button
                className="button button--secondary"
                disabled={busy !== null}
                onClick={() => onVerify(source)}
                type="button"
              >
                Verify source
              </button>
            )}
            {source.status === "verified" && (
              <button
                className="button button--quiet"
                disabled={busy !== null}
                onClick={() => onMarkStale(source.id)}
                type="button"
              >
                Mark stale
              </button>
            )}
          </div>
        </article>
      ))}
      {data.sources.length === 0 && (
        <div className="guidance-empty">No sources are recorded.</div>
      )}
    </div>
  );
}

function Rag({
  data,
  busy,
  onReindex,
}: {
  data: AdminDashboardData;
  busy: string | null;
  onReindex: (sourceId: number) => void;
}) {
  return (
    <div className="admin-record-list">
      <div className="admin-info-note">
        Re-indexing is available through the protected document ingestion API.
        Existing verified-source checks and content-hash duplicate prevention
        remain in force.
      </div>
      {data.ingestion.map((item) => (
        <article className="admin-record" key={item.id}>
          <Database aria-hidden="true" size={19} />
          <div className="admin-record-main">
            <h2>{item.scheme_name}</h2>
            <p>{item.url}</p>
            <p>
              {item.indexed
                ? `${item.indexed_chunks} chunks indexed`
                : "No indexed chunks"}{" "}
              · {item.status}
            </p>
            {item.latest_failure && (
              <p className="admin-error-detail">{item.latest_failure}</p>
            )}
          </div>
          {item.status === "verified" && (
            <button
              className="button button--secondary"
              disabled={busy !== null}
              onClick={() => onReindex(item.id)}
              type="button"
            >
              Re-index source
            </button>
          )}
        </article>
      ))}
      {data.failed_extractions.map((failure) => (
        <article
          className="admin-record admin-record--warning"
          key={`failure-${failure.id}`}
        >
          <FileWarning aria-hidden="true" size={19} />
          <div className="admin-record-main">
            <h2>
              Extraction failure · source {failure.source_id ?? "unknown"}
            </h2>
            <p>{failure.error || "No error details recorded."}</p>
            <p>{dateLabel(failure.created_at)}</p>
          </div>
        </article>
      ))}
      {data.ingestion.length === 0 && data.failed_extractions.length === 0 && (
        <div className="guidance-empty">
          No documents are indexed or failed.
        </div>
      )}
    </div>
  );
}

function Corrections({
  data,
  busy,
  onReview,
}: {
  data: AdminDashboardData;
  busy: string | null;
  onReview: (id: number, status: "in_review" | "resolved" | "declined") => void;
}) {
  return (
    <div className="admin-record-list">
      {data.corrections.map((report) => (
        <article className="admin-record" key={report.id}>
          <div className="admin-record-main">
            <h2>
              {report.report_type.replaceAll("_", " ")} ·{" "}
              {report.status.replaceAll("_", " ")}
            </h2>
            <p>{report.description}</p>
            <p>
              Scheme record {report.scheme_id ?? "no longer available"} ·{" "}
              {dateLabel(report.created_at)}
            </p>
            {report.review_notes && <p>Review note: {report.review_notes}</p>}
          </div>
          <div className="admin-actions">
            <button
              className="button button--secondary"
              disabled={busy !== null}
              onClick={() => onReview(report.id, "in_review")}
              type="button"
            >
              Review
            </button>
            <button
              className="button button--quiet"
              disabled={busy !== null}
              onClick={() => onReview(report.id, "resolved")}
              type="button"
            >
              Resolve
            </button>
            <button
              className="button button--quiet"
              disabled={busy !== null}
              onClick={() => onReview(report.id, "declined")}
              type="button"
            >
              Decline
            </button>
          </div>
        </article>
      ))}
      {data.corrections.length === 0 && (
        <div className="guidance-empty">
          No corrections are awaiting review.
        </div>
      )}
    </div>
  );
}

function Feedback({ data }: { data: AdminDashboardData }) {
  return (
    <div className="admin-record-list">
      {data.assistant_feedback.map((item) => (
        <article className="admin-record" key={item.message_id}>
          <ThumbsDown aria-hidden="true" size={19} />
          <div className="admin-record-main">
            <h2>
              {item.feedback.replaceAll("_", " ")} · assistant response{" "}
              {item.message_id}
            </h2>
            <p>{item.content}</p>
            <p>{dateLabel(item.created_at)}</p>
          </div>
        </article>
      ))}
      {data.assistant_feedback.length === 0 && (
        <div className="guidance-empty">
          No assistant feedback has been submitted.
        </div>
      )}
    </div>
  );
}

function Audit({ data }: { data: AdminDashboardData }) {
  return (
    <div className="admin-record-list">
      {data.audit_logs.map((item) => (
        <article className="admin-record" key={item.id}>
          <History aria-hidden="true" size={19} />
          <div className="admin-record-main">
            <h2>{item.action}</h2>
            <p>
              {item.entity_type} {item.entity_id ?? ""} · actor{" "}
              {item.actor_user_id ?? "system"} · {dateLabel(item.created_at)}
            </p>
            {item.details && <pre>{JSON.stringify(item.details, null, 2)}</pre>}
          </div>
        </article>
      ))}
    </div>
  );
}

function Reviews({ data }: { data: AdminDashboardData }) {
  return (
    <div className="admin-record-list">
      {data.review_history.map((item) => (
        <article className="admin-record" key={item.id}>
          <Check aria-hidden="true" size={19} />
          <div className="admin-record-main">
            <h2>{item.action}</h2>
            <p>
              Scheme {item.scheme_id ?? "removed"} · reviewer{" "}
              {item.actor_user_id} · {dateLabel(item.created_at)}
            </p>
            <p>{item.reason}</p>
            {item.before_snapshot && (
              <details>
                <summary>Before / after snapshots</summary>
                <pre>{JSON.stringify(item.before_snapshot, null, 2)}</pre>
                <pre>{JSON.stringify(item.after_snapshot, null, 2)}</pre>
              </details>
            )}
          </div>
        </article>
      ))}
      {data.review_history.length === 0 && (
        <div className="guidance-empty">No review history is recorded.</div>
      )}
    </div>
  );
}
