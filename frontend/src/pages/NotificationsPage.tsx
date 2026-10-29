import { Bell, CheckCheck, ExternalLink, Settings2 } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import {
  notificationService,
  type NotificationPage,
  type NotificationPreferences,
} from "../lib/notifications";

function NotificationError({ message }: { message: string }) {
  return (
    <p className="inline-error" role="alert">
      {message}
    </p>
  );
}

export function NotificationsPage() {
  const [page, setPage] = useState<NotificationPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function load() {
    try {
      setPage(await notificationService.list());
      setError(null);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not load your notifications.",
      );
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function toggleRead(id: number, read: boolean) {
    setBusyId(id);
    try {
      await notificationService.setRead(id, read);
      await load();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not update this notification.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section aria-labelledby="notifications-title" className="guidance-page">
      <header className="guidance-header">
        <p className="eyebrow">Your updates</p>
        <h1 id="notifications-title">Notifications</h1>
        <p>
          Deadline alerts are created only from current, verified deadline
          records. Always check the linked official source.
        </p>
      </header>
      <div className="notification-toolbar">
        <span>{page?.unread_count ?? 0} unread</span>
        <Link className="button button--secondary" to="/settings">
          <Settings2 aria-hidden="true" size={16} />
          Notification settings
        </Link>
      </div>
      {error && <NotificationError message={error} />}
      {!page && !error && (
        <div aria-live="polite" className="guidance-state">
          Loading notifications…
        </div>
      )}
      {page && page.items.length > 0 && (
        <div className="notification-list">
          {page.items.map((notification) => (
            <article
              className={`notification-card${notification.read_at ? "" : "notification-card--unread"}`}
              key={notification.id}
            >
              <Bell
                aria-hidden="true"
                className="notification-icon"
                size={19}
              />
              <div className="notification-copy">
                <div className="notification-heading">
                  <h2>{notification.title}</h2>
                  {!notification.read_at && (
                    <span className="notification-unread-label">New</span>
                  )}
                </div>
                <p>{notification.message}</p>
                {notification.deadline_at && (
                  <p className="notification-metadata">
                    Deadline:{" "}
                    {new Intl.DateTimeFormat(undefined, {
                      dateStyle: "medium",
                      timeStyle: "short",
                    }).format(new Date(notification.deadline_at))}
                  </p>
                )}
                {notification.source_url && (
                  <>
                    <a
                      className="notification-source"
                      href={notification.source_url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      Verify with official source
                      <ExternalLink aria-hidden="true" size={14} />
                    </a>
                    <p className="notification-metadata">
                      Source last verified:{" "}
                      {notification.source_verified_at
                        ? new Intl.DateTimeFormat(undefined, {
                            dateStyle: "medium",
                          }).format(new Date(notification.source_verified_at))
                        : "date unavailable"}
                    </p>
                  </>
                )}
                {!notification.is_valid && (
                  <p className="guidance-warning">
                    This reminder was withdrawn because its deadline or source
                    changed. Do not rely on the former date.
                  </p>
                )}
                {notification.email_delivery_status === "failed" && (
                  <p className="guidance-warning">
                    Email delivery failed. This alert remains available here.
                  </p>
                )}
              </div>
              <button
                className="button button--quiet notification-read-button"
                disabled={busyId === notification.id}
                onClick={() =>
                  void toggleRead(notification.id, !notification.read_at)
                }
                type="button"
              >
                <CheckCheck aria-hidden="true" size={15} />
                {notification.read_at ? "Mark unread" : "Mark read"}
              </button>
            </article>
          ))}
        </div>
      )}
      {page && page.items.length === 0 && (
        <div className="guidance-empty">
          <Bell aria-hidden="true" size={28} />
          <h2>You’re all caught up</h2>
          <p>
            There are no notifications yet. Verified deadline reminders appear
            here when a saved or tracked scheme has a confirmed upcoming date.
          </p>
        </div>
      )}
    </section>
  );
}

export function NotificationSettingsPage() {
  const [preferences, setPreferences] =
    useState<NotificationPreferences | null>(null);
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    notificationService
      .getPreferences()
      .then((result) => {
        setPreferences(result);
        setTimezone(result.timezone);
      })
      .catch((cause: unknown) =>
        setError(
          cause instanceof Error
            ? cause.message
            : "Could not load notification preferences.",
        ),
      );
  }, []);

  function setBoolean(
    field:
      | "in_app_enabled"
      | "email_enabled"
      | "reminders_enabled"
      | "deadline_reminders_enabled",
    value: boolean,
  ) {
    setSaved(false);
    setPreferences((current) =>
      current ? { ...current, [field]: value } : current,
    );
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!preferences) return;
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const updated = await notificationService.updatePreferences({
        in_app_enabled: preferences.in_app_enabled,
        email_enabled: preferences.email_enabled,
        reminders_enabled: preferences.reminders_enabled,
        deadline_reminders_enabled: preferences.deadline_reminders_enabled,
        timezone,
      });
      setPreferences(updated);
      setTimezone(updated.timezone);
      setSaved(true);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not save notification preferences.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section
      aria-labelledby="notification-settings-title"
      className="guidance-page"
    >
      <header className="guidance-header">
        <p className="eyebrow">Your account</p>
        <h1 id="notification-settings-title">Notification settings</h1>
        <p>
          Choose where deadline reminders are delivered. Email is optional and
          is sent only when the backend email provider is configured.
        </p>
      </header>
      {error && <NotificationError message={error} />}
      {!preferences && !error && (
        <div aria-live="polite" className="guidance-state">
          Loading settings…
        </div>
      )}
      {preferences && (
        <form className="notification-settings" onSubmit={save}>
          <label className="notification-setting">
            <input
              checked={preferences.in_app_enabled}
              onChange={(event) =>
                setBoolean("in_app_enabled", event.target.checked)
              }
              type="checkbox"
            />
            <span>
              <strong>In-app notifications</strong>
              <small>Keep reminders in your notification history.</small>
            </span>
          </label>
          <label className="notification-setting">
            <input
              checked={preferences.email_enabled}
              onChange={(event) =>
                setBoolean("email_enabled", event.target.checked)
              }
              type="checkbox"
            />
            <span>
              <strong>Email notifications</strong>
              <small>
                Send optional reminders to your account email address.
              </small>
            </span>
          </label>
          <label className="notification-setting">
            <input
              checked={preferences.reminders_enabled}
              onChange={(event) =>
                setBoolean("reminders_enabled", event.target.checked)
              }
              type="checkbox"
            />
            <span>
              <strong>Scheme and application reminders</strong>
              <small>
                Receive reminders for schemes you save or applications you
                track.
              </small>
            </span>
          </label>
          <label className="notification-setting">
            <input
              checked={preferences.deadline_reminders_enabled}
              onChange={(event) =>
                setBoolean("deadline_reminders_enabled", event.target.checked)
              }
              type="checkbox"
            />
            <span>
              <strong>Verified deadline reminders</strong>
              <small>
                Reminders are sent only when a deadline and its source are
                current and verified.
              </small>
            </span>
          </label>
          <label className="notification-timezone">
            Time zone for reminder dates
            <input
              autoComplete="off"
              maxLength={80}
              onChange={(event) => {
                setTimezone(event.target.value);
                setSaved(false);
              }}
              placeholder="Asia/Kolkata"
              required
              value={timezone}
            />
            <small>Use an IANA time zone, for example Asia/Kolkata.</small>
          </label>
          <button
            className="button button--primary"
            disabled={saving}
            type="submit"
          >
            {saving ? "Saving…" : "Save preferences"}
          </button>
          {saved && (
            <p className="notification-saved" role="status">
              Your notification preferences have been saved.
            </p>
          )}
        </form>
      )}
    </section>
  );
}
