import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "../src/App";
import { authService } from "../src/lib/auth";
import { schemeService } from "../src/lib/schemes/service";
import { jobService } from "../src/lib/jobs";
import type { Scheme } from "../src/lib/schemes/types";

vi.mock("../src/lib/auth", () => ({
  authService: {
    getCurrentUser: vi.fn(),
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
    logout: vi.fn(),
  },
}));

vi.mock("../src/lib/schemes/service", () => ({
  schemeService: {
    getSchemes: vi.fn(),
    getSchemeById: vi.fn(),
    assessEligibility: vi.fn(),
    getRecommendations: vi.fn(),
    getDashboardSummary: vi.fn(),
  },
}));

vi.mock("../src/lib/jobs", () => ({
  jobService: {
    listJobs: vi.fn(),
    getJob: vi.fn(),
    getRecommendations: vi.fn(),
  },
}));

const signedInUser = {
  id: 12,
  email: "rahul@example.com",
  full_name: "Rahul Kumar",
  profile_complete: true,
};

const profile = {
  ...signedInUser,
  age: 23,
  state: "Bihar",
  district: "Patna",
  area_type: "Urban",
  occupation: "Student",
  occupation_other: null,
  employment_status: "Student",
  worker_category: null,
  education_level: "Graduate",
  qualification: null,
  field_of_study: null,
  years_experience: null,
  preferred_job_roles: [],
  preferred_job_states: [],
  current_student: true,
  annual_income_range: "₹2–3 lakh",
  household_size: 4,
  beneficiary_categories: ["Students"],
  profile_complete: true,
};

const schemes: Scheme[] = [
  {
    id: "test-education",
    name: "Education Support Test Fixture",
    shortDescription: "A reviewed test record for education support.",
    category: "Education",
    beneficiaries: ["Students"],
    governmentLevel: "Central",
    keywords: ["education"],
    benefits: ["Test benefit."],
    eligibilityCriteria: ["Test criterion."],
    requiredDocuments: ["Test document."],
    applicationProcedure: ["Test step."],
    officialSource: "https://official.gov.in/education",
    lastVerifiedDate: "2026-10-25",
    dataStatus: "verified",
  },
];

const recommendations = {
  profile_complete: true,
  completion_percentage: 100,
  missing_profile_fields: [],
  items: [
    {
      scheme_id: "test-education",
      scheme_name: "Education Support Test Fixture",
      short_description: "A reviewed test record for education support.",
      category: "Education",
      data_status: "verified" as const,
      eligibility_status: "unable_to_determine" as const,
      summary: "The recorded criteria need confirmation.",
      reasons: [
        "Your selected beneficiary group “Students” matches the recorded target audience.",
      ],
      criteria: [
        {
          rule_id: 1,
          criterion: "Test age rule",
          profile_field: null,
          result: "requires_confirmation" as const,
          explanation: "This criterion needs confirmation.",
          required: true,
          evaluated_value: null,
          rule_source_references: [],
          uncertainty_reason: "This rule needs human confirmation.",
        },
      ],
      missing_information: [],
      sources: [],
    },
  ],
  page: 1,
  page_size: 6,
  total: 1,
  pages: 1,
};

const dashboardSummary = {
  application_total: 0,
  application_status_counts: {},
  verified_upcoming_deadlines: [],
};

describe("dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(authService.getCurrentUser).mockResolvedValue(signedInUser);
    vi.mocked(authService.getProfile).mockResolvedValue(profile);
    vi.mocked(schemeService.getSchemes).mockResolvedValue(schemes);
    vi.mocked(schemeService.getRecommendations).mockResolvedValue(
      recommendations,
    );
    vi.mocked(schemeService.getDashboardSummary).mockResolvedValue(
      dashboardSummary,
    );
    vi.mocked(jobService.getRecommendations).mockResolvedValue({
      items: [],
      profile_complete: true,
    });
  });

  it("shows a personalized overview without implying eligibility", async () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", { name: "Welcome, Rahul" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", {
        name: "Education Support Test Fixture",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("23 years · Bihar · Graduate")).toBeInTheDocument();
    expect(screen.getByText("Profile completion")).toBeInTheDocument();
    expect(screen.queryByText("Potentially eligible")).not.toBeInTheDocument();
    expect(screen.getByText("Unable to determine")).toBeInTheDocument();
    expect(screen.getByText(/matches the recorded target audience/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Discover schemes" }),
    ).toHaveAttribute("href", "/schemes");
    expect(
      screen.getByRole("link", { name: "SchemeSathi AI dashboard" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "Main navigation" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/independent civic-tech project ·/i),
    ).not.toBeInTheDocument();
  });

  it("keeps scheme discovery inside the signed-in workspace", async () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    await screen.findByRole("heading", { name: "Welcome, Rahul" });
    fireEvent.click(screen.getByRole("link", { name: "Discover schemes" }));

    expect(
      await screen.findByRole("heading", {
        name: "Explore Government Schemes",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("complementary", { name: "Dashboard navigation" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Discover schemes" })).toHaveClass(
      "active",
    );
    expect(screen.getByRole("link", { name: "Saved schemes" })).toHaveAttribute(
      "href",
      "/saved-schemes",
    );
    expect(
      screen.queryByRole("navigation", { name: "Main navigation" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument();
  });

  it("takes a signed-in user from the root page to the dashboard", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", { name: "Welcome, Rahul" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /discover government benefits/i }),
    ).not.toBeInTheDocument();
  });

  it("takes a signed-in user with an incomplete profile to onboarding", async () => {
    vi.mocked(authService.getCurrentUser).mockResolvedValue({
      ...signedInUser,
      profile_complete: false,
    });

    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", { name: "Welcome" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /discover government benefits/i }),
    ).not.toBeInTheDocument();
  });

  it("prompts users with incomplete profiles and handles no matches", async () => {
    vi.mocked(schemeService.getRecommendations).mockResolvedValue({
      ...recommendations,
      profile_complete: false,
      completion_percentage: 66,
      missing_profile_fields: ["Education level"],
      items: [],
      total: 0,
      pages: 0,
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText(/complete your profile to improve discovery/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Complete profile" }),
    ).toHaveAttribute("href", "/profile");
    expect(
      screen.getByText(/no relevant scheme records could be matched yet/i),
    ).toBeInTheDocument();
  });
});
