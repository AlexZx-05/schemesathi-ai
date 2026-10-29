import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  NotificationsPage,
  NotificationSettingsPage,
} from "../src/pages/NotificationsPage";
import { notificationService } from "../src/lib/notifications";

vi.mock("../src/lib/notifications", () => ({
  notificationService: {
    getPreferences: vi.fn(),
    updatePreferences: vi.fn(),
    list: vi.fn(),
    setRead: vi.fn(),
  },
}));

const preferences = {
  in_app_enabled: true,
  email_enabled: false,
  reminders_enabled: true,
  deadline_reminders_enabled: true,
  timezone: "Asia/Kolkata",
  updated_at: null,
};

describe("notification pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows source-backed reminders and persists read state", async () => {
    vi.mocked(notificationService.list).mockResolvedValue({
      items: [
        {
          id: 12,
          notification_type: "verified_deadline_reminder",
          title: "Example scheme deadline in 7 day(s)",
          message: "Check the official source.",
          created_at: "2026-10-23T10:00:00Z",
          read_at: null,
          is_valid: true,
          deadline_at: "2026-10-30T10:00:00Z",
          source_url: "https://official.gov.in/scheme",
          source_verified_at: "2026-10-22T10:00:00Z",
          email_delivery_status: "not_requested",
        },
      ],
      unread_count: 1,
      page: 1,
      page_size: 20,
      total: 1,
    });
    vi.mocked(notificationService.setRead).mockResolvedValue({
      id: 12,
      notification_type: "verified_deadline_reminder",
      title: "Example scheme deadline in 7 day(s)",
      message: "Check the official source.",
      created_at: "2026-10-23T10:00:00Z",
      read_at: "2026-10-23T10:05:00Z",
      is_valid: true,
      deadline_at: "2026-10-30T10:00:00Z",
      source_url: "https://official.gov.in/scheme",
      source_verified_at: "2026-10-22T10:00:00Z",
      email_delivery_status: "not_requested",
    });

    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", {
        name: "Example scheme deadline in 7 day(s)",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /verify with official source/i }),
    ).toHaveAttribute("href", "https://official.gov.in/scheme");
    fireEvent.click(screen.getByRole("button", { name: /mark read/i }));
    await waitFor(() =>
      expect(notificationService.setRead).toHaveBeenCalledWith(12, true),
    );
  });

  it("saves optional email and timezone preferences", async () => {
    vi.mocked(notificationService.getPreferences).mockResolvedValue(
      preferences,
    );
    vi.mocked(notificationService.updatePreferences).mockResolvedValue({
      ...preferences,
      email_enabled: true,
      timezone: "America/Los_Angeles",
    });

    render(<NotificationSettingsPage />);

    const emailToggle = await screen.findByRole("checkbox", {
      name: /email notifications/i,
    });
    fireEvent.click(emailToggle);
    fireEvent.change(screen.getByLabelText(/time zone for reminder dates/i), {
      target: { value: "America/Los_Angeles" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save preferences/i }));

    await waitFor(() =>
      expect(notificationService.updatePreferences).toHaveBeenCalledWith({
        in_app_enabled: true,
        email_enabled: true,
        reminders_enabled: true,
        deadline_reminders_enabled: true,
        timezone: "America/Los_Angeles",
      }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent(
      /preferences have been saved/i,
    );
  });
});
