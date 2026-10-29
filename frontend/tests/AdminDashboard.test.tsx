import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuth } from "../src/context/AuthContext";
import { adminService } from "../src/lib/admin";
import { AdminDashboardPage } from "../src/pages/AdminDashboardPage";

vi.mock("../src/context/AuthContext", () => ({ useAuth: vi.fn() }));
vi.mock("../src/lib/admin", () => ({
  adminService: {
    dashboard: vi.fn(),
    createScheme: vi.fn(),
    createCategory: vi.fn(),
    updateCategory: vi.fn(),
    deleteCategory: vi.fn(),
    verifyScheme: vi.fn(),
    updateScheme: vi.fn(),
    verifySource: vi.fn(),
    recordSourceReview: vi.fn(),
    markSourceStale: vi.fn(),
    reindexSource: vi.fn(),
    createSource: vi.fn(),
    createEligibilityRule: vi.fn(),
    createDocumentRequirement: vi.fn(),
    createDeadline: vi.fn(),
    reviewCorrection: vi.fn(),
  },
}));

const dashboard = {
  administrator: { id: 3, name: "Admin User" },
  counts: { schemes: 1, verified_schemes: 0 },
  categories: [
    {
      id: 9,
      name: "Education",
      slug: "education",
      description: "Education support.",
      scheme_count: 1,
    },
  ],
  schemes: [
    {
      id: 12,
      slug: "education-support",
      name: "Education Support",
      description: "A recorded scheme description.",
      benefits: null,
      department: null,
      government_level: "Central",
      beneficiaries: [],
      keywords: [],
      application_instructions: null,
      status: "active",
      verification_status: "unverified",
      requires_human_review: true,
      reviewed_by_user_id: null,
      last_verified_at: null,
      official_application_url: null,
      category_names: ["Education"],
      issue_flags: [
        "Missing official application URL",
        "Human review required",
      ],
      source_count: 0,
      rule_count: 0,
      document_count: 0,
      eligibility_rules: [],
      documents: [],
      deadlines: [],
    },
  ],
  sources: [],
  ingestion: [],
  failed_extractions: [],
  corrections: [],
  assistant_feedback: [],
  audit_logs: [],
  review_history: [],
};

function setUser(isAdmin: boolean) {
  vi.mocked(useAuth).mockReturnValue({
    status: "authenticated",
    user: {
      id: 3,
      email: "admin@example.com",
      full_name: "Admin User",
      profile_complete: true,
      is_admin: isAdmin,
    },
    error: null,
    login: vi.fn(),
    googleLogin: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    updateUser: vi.fn(),
    retrySession: vi.fn(),
  });
}

describe("administrator dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(adminService.dashboard).mockResolvedValue(dashboard);
  });

  it("shows a protected access state to ordinary users without requesting admin data", () => {
    setUser(false);
    render(<AdminDashboardPage />);

    expect(screen.getByRole("alert")).toHaveTextContent(
      /administrator access is required/i,
    );
    expect(adminService.dashboard).not.toHaveBeenCalled();
  });

  it("loads quality flags and opens category management for administrators", async () => {
    setUser(true);
    render(<AdminDashboardPage />);

    expect(
      await screen.findByRole("heading", {
        name: "Scheme data administration",
      }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Schemes & quality" }));
    expect(
      screen.getByText("Missing official application URL"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Categories" }));
    expect(
      screen.getByRole("heading", { name: "Education" }),
    ).toBeInTheDocument();
    expect(adminService.dashboard).toHaveBeenCalledTimes(1);
  });

  it("allows administrators to edit source-backed scheme information", async () => {
    setUser(true);
    render(<AdminDashboardPage />);

    await screen.findByRole("heading", {
      name: "Scheme data administration",
    });
    fireEvent.click(screen.getByRole("button", { name: "Schemes & quality" }));
    fireEvent.click(screen.getByText("Edit scheme information"));
    fireEvent.change(screen.getByLabelText("Source-backed overview"), {
      target: { value: "A source-backed overview of this scheme." },
    });
    fireEvent.change(screen.getByLabelText("Benefits (one per line)"), {
      target: { value: "Benefit one\nBenefit two" },
    });
    fireEvent.change(screen.getByLabelText("Change reason"), {
      target: { value: "Updated from the current official source." },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Save scheme information" }),
    );

    expect(adminService.updateScheme).toHaveBeenCalledWith(
      "education-support",
      expect.objectContaining({
        description: "A source-backed overview of this scheme.",
        benefits: "Benefit one\nBenefit two",
        reason: "Updated from the current official source.",
      }),
    );
  });
});
