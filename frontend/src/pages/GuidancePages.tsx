import { useEffect, useState } from "react";
import { ExternalLink, FileCheck2, ListChecks, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  guidanceService,
  type ApplicationGuidance,
  type ApplicationStatus,
  type ApplicationTracking,
  type DocumentChecklist,
  type SavedScheme,
} from "../lib/guidance";

const statusLabels: Record<ApplicationStatus, string> = {
  planning: "Planning to apply",
  preparing_documents: "Preparing documents",
  ready_to_apply: "Ready to apply",
  submitted_externally: "Submitted externally",
  in_progress: "In progress",
  completed: "Completed",
  not_proceeding: "Not proceeding",
};

function PageState({ error }: { error: string }) {
  return <section className="guidance-page"><div className="guidance-state" role="alert">{error}</div></section>;
}

export function SavedSchemesPage() {
  const [items, setItems] = useState<SavedScheme[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { guidanceService.listSaved().then(setItems).catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load saved schemes.")); }, []);
  async function remove(item: SavedScheme) {
    if (!window.confirm(`Remove ${item.scheme_name} from your saved schemes?`)) return;
    try { await guidanceService.unsave(item.scheme_id); setItems((current) => current.filter((saved) => saved.id !== item.id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not remove the saved scheme."); }
  }
  if (error) return <PageState error={error} />;
  return <section className="guidance-page" aria-labelledby="saved-title"><header className="guidance-header"><p className="eyebrow">Your shortlist</p><h1 id="saved-title">Saved schemes</h1><p>Saved records stay tied to your account. Check their current verification status before taking action.</p></header>{items.length ? <div className="guidance-card-grid">{items.map((item) => <article className="guidance-card" key={item.id}><div><span className={`guidance-status guidance-status--${item.guidance_available ? "available" : "unavailable"}`}>{item.guidance_available ? "Guidance available" : "Needs review"}</span><h2>{item.scheme_name}</h2><p>{item.scheme_status} · {item.verification_status}</p><p>{item.last_verified_at ? `Last verified ${new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(item.last_verified_at))}` : "Verification date unavailable"}</p>{item.availability_notice && <p className="guidance-warning">{item.availability_notice}</p>}</div><div className="guidance-card-actions"><Link className="button button--secondary" to={`/schemes/${item.scheme_id}`}>View scheme</Link><button className="button button--quiet" onClick={() => void remove(item)} type="button"><Trash2 aria-hidden="true" size={16}/> Remove</button></div></article>)}</div> : <div className="guidance-empty"><ShieldCheck aria-hidden="true" size={28}/><h2>No saved schemes yet</h2><p>Save a scheme to keep its status and source information handy.</p><Link className="button button--primary" to="/schemes">Browse schemes</Link></div>}</section>;
}

export function DocumentsPage() {
  const { schemeId } = useParams(); const [checklist, setChecklist] = useState<DocumentChecklist | null>(null); const [error, setError] = useState<string | null>(null);
  useEffect(() => { if (schemeId) guidanceService.getChecklist(schemeId).then(setChecklist).catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load the document checklist.")); }, [schemeId]);
  async function toggle(documentId: number, ready: boolean) { if (!schemeId || !checklist) return; try { const updated = await guidanceService.setDocumentReady(schemeId, documentId, ready); setChecklist({ ...checklist, items: checklist.items.map((item) => item.document_id === documentId ? updated : item) }); } catch (e) { setError(e instanceof Error ? e.message : "Could not update this checklist item."); } }
  if (error) return <PageState error={error} />; if (!checklist) return <PageState error="Loading document checklist…" />;
  return <section className="guidance-page" aria-labelledby="documents-title"><header className="guidance-header"><p className="eyebrow">Preparation checklist</p><h1 id="documents-title">Documents for {checklist.scheme_name}</h1><p>{checklist.notice}</p></header><div className="guidance-checklist">{checklist.items.map((item) => <label key={item.document_id}><input checked={item.ready} onChange={(event) => void toggle(item.document_id, event.target.checked)} type="checkbox"/><span><strong>{item.name}</strong><small>{item.is_required ? "Required record" : "May be requested"}{item.description ? ` · ${item.description}` : ""}</small>{item.uncertainty_notice && <em>{item.uncertainty_notice}</em>}</span><FileCheck2 aria-hidden="true" size={19}/></label>)}</div><aside className="guidance-source-note"><ShieldCheck aria-hidden="true" size={18}/><span>Verify requirements with the official source. Marking an item complete does not validate it.</span></aside><Link className="button button--primary" to={`/schemes/${checklist.scheme_id}/apply`}>Continue to application guidance</Link></section>;
}

export function ApplyPage() {
  const { schemeId } = useParams(); const navigate = useNavigate(); const [guidance, setGuidance] = useState<ApplicationGuidance | null>(null); const [error, setError] = useState<string | null>(null); const [creating, setCreating] = useState(false);
  useEffect(() => { if (schemeId) guidanceService.getApplicationGuidance(schemeId).then(setGuidance).catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load application guidance.")); }, [schemeId]);
  async function track() { if (!schemeId) return; setCreating(true); try { const application = await guidanceService.createApplication(schemeId); navigate(`/applications/${application.id}`); } catch (e) { setError(e instanceof Error ? e.message : "Could not create application tracking."); } finally { setCreating(false); } }
  if (error) return <PageState error={error} />; if (!guidance) return <PageState error="Loading application guidance…" />;
  return <section className="guidance-page" aria-labelledby="apply-title"><header className="guidance-header"><p className="eyebrow">Apply through the official channel</p><h1 id="apply-title">Application guidance</h1><p>{guidance.scheme_name}</p></header><div className="guidance-steps">{guidance.application_steps.length ? <ol>{guidance.application_steps.map((step) => <li key={step}>{step}</li>)}</ol> : <p>No structured application steps are recorded. Use the verified source to confirm the process.</p>}</div><aside className="guidance-source-note"><ListChecks aria-hidden="true" size={18}/><span>{guidance.checklist_complete ? "Your recorded required checklist items are ready." : `${guidance.checklist_required_remaining} required checklist item(s) are still unmarked.`}</span></aside><p className="guidance-warning">{guidance.submission_notice}</p><div className="guidance-card-actions">{guidance.official_application_url && <a className="button button--primary" href={guidance.official_application_url} rel="noreferrer" target="_blank">Open official portal <ExternalLink aria-hidden="true" size={16}/></a>}<button className="button button--secondary" disabled={creating} onClick={() => void track()} type="button"><Plus aria-hidden="true" size={16}/>{creating ? "Creating…" : "Track my application"}</button></div></section>;
}

export function ApplicationsPage() {
  const [items, setItems] = useState<ApplicationTracking[]>([]); const [filter, setFilter] = useState<"all" | ApplicationStatus>("all"); const [error, setError] = useState<string | null>(null);
  useEffect(() => { guidanceService.listApplications(filter === "all" ? undefined : filter).then(setItems).catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load application tracking.")); }, [filter]);
  if (error) return <PageState error={error} />;
  return <section className="guidance-page" aria-labelledby="applications-title"><header className="guidance-header"><p className="eyebrow">Your self-reported progress</p><h1 id="applications-title">Application tracking</h1><p>Tracking is private to your account. “Submitted externally” is only recorded after your confirmation.</p></header><label className="guidance-filter">Filter status <select onChange={(event) => setFilter(event.target.value as "all" | ApplicationStatus)} value={filter}><option value="all">All statuses</option>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>{items.length ? <div className="guidance-card-grid">{items.map((item) => <article className="guidance-card" key={item.id}><div><span className="guidance-status guidance-status--available">{statusLabels[item.status]}</span><h2>{item.scheme_name}</h2><div aria-label={`${item.progress_percent}% progress`} className="guidance-progress"><span style={{ width: `${item.progress_percent}%` }}/></div><p>{item.progress_percent}% tracked progress</p></div><Link className="button button--secondary" to={`/applications/${item.id}`}>Manage</Link></article>)}</div> : <div className="guidance-empty"><ListChecks aria-hidden="true" size={28}/><h2>No tracked applications</h2><p>Start from a scheme’s application guidance when you are ready to plan.</p><Link className="button button--primary" to="/schemes">Browse schemes</Link></div>}</section>;
}

export function ApplicationDetailPage() {
  const { applicationId } = useParams(); const [item, setItem] = useState<ApplicationTracking | null>(null); const [status, setStatus] = useState<ApplicationStatus>("planning"); const [notes, setNotes] = useState(""); const [error, setError] = useState<string | null>(null);
  useEffect(() => { if (applicationId) guidanceService.getApplication(Number(applicationId)).then((application) => { setItem(application); setStatus(application.status); setNotes(application.notes ?? ""); }).catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load this application.")); }, [applicationId]);
  async function update() { if (!item) return; const confirming = status === "submitted_externally" && status !== item.status; if (confirming && !window.confirm("Confirm that you submitted this application yourself through the official external portal. SchemeSathi cannot verify the submission.")) return; try { const updated = await guidanceService.updateApplication(item.id, { status, notes, confirm_external_submission: confirming }); setItem(updated); } catch (e) { setError(e instanceof Error ? e.message : "Could not update application tracking."); } }
  if (error) return <PageState error={error} />; if (!item) return <PageState error="Loading application…" />;
  return <section className="guidance-page" aria-labelledby="application-title"><header className="guidance-header"><p className="eyebrow">Application tracker</p><h1 id="application-title">{item.scheme_name}</h1><p>Created {new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(item.created_at))}</p></header><div className="guidance-detail-form"><label>Status<select onChange={(event) => setStatus(event.target.value as ApplicationStatus)} value={status}>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Private notes<textarea maxLength={2000} onChange={(event) => setNotes(event.target.value)} value={notes}/></label><button className="button button--primary" onClick={() => void update()} type="button">Save progress</button></div><aside className="guidance-source-note"><ShieldCheck aria-hidden="true" size={18}/><span>Only mark “Submitted externally” after you have submitted through the official government portal. Never enter portal passwords here.</span></aside></section>;
}
