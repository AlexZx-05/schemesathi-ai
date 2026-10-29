import { apiRequest } from "./api";

export interface NotificationPreferences {
  in_app_enabled: boolean;
  email_enabled: boolean;
  reminders_enabled: boolean;
  deadline_reminders_enabled: boolean;
  timezone: string;
  updated_at: string | null;
}

export interface SchemeNotification {
  id: number;
  notification_type: string;
  title: string;
  message: string;
  created_at: string;
  read_at: string | null;
  is_valid: boolean;
  deadline_at: string | null;
  source_url: string | null;
  source_verified_at: string | null;
  email_delivery_status:
    | "not_requested"
    | "pending"
    | "sending"
    | "sent"
    | "failed"
    | "skipped"
    | "invalidated";
}

export interface NotificationPage {
  items: SchemeNotification[];
  unread_count: number;
  page: number;
  page_size: number;
  total: number;
}

export const notificationService = {
  getPreferences: () =>
    apiRequest<NotificationPreferences>("/api/v1/notifications/preferences"),
  updatePreferences: (
    preferences: Omit<NotificationPreferences, "updated_at">,
  ) =>
    apiRequest<NotificationPreferences>("/api/v1/notifications/preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(preferences),
    }),
  list: (page = 1) =>
    apiRequest<NotificationPage>(
      `/api/v1/notifications?page=${page}&page_size=20`,
    ),
  setRead: (notificationId: number, read: boolean) =>
    apiRequest<SchemeNotification>(
      `/api/v1/notifications/${notificationId}/read`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ read }),
      },
    ),
};
