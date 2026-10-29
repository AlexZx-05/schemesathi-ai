import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "../src/App";
import { authService } from "../src/lib/auth";
import { schemeService } from "../src/lib/schemes/service";
import type { EligibilityAssessment } from "../src/lib/schemes/service";
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

const scheme: Scheme = {
  id: "test-education",
  name: "Education Support Test Fixture",
  shortDescription: "A reviewed test record for education support.",
  category: "Education",
  beneficiaries: ["Students"],
  governmentLevel: "Central",
  keywords: ["education"],
  benefits: ["Test benefit."],
  eligibilityCriteria: ["Age requirement"],
  requiredDocuments: [],
  applicationProcedure: [],
  officialSource: null,
  lastVerifiedDate: null,
  dataStatus: "verified",
};

const savedProfileAssessment: EligibilityAssessment = {
  scheme_id: "test-education",
  scheme_name: "Education Support Test Fixture",
  outcome: "more_information_required",
  summary: "More information or confirmation is needed.",
  criteria: [
    {
      rule_id: 1,
      criterion: "Age must be at least 21",
      profile_field: "age",
      result: "unknown",
      explanation: "Add age to your profile or provide a temporary answer.",
      required: true,
      evaluated_value: null,
      rule_source_references: [
        {
          title: "Verified source",
          url: "https://example.gov.in/scheme",
          last_verified_at: "2026-10-22T08:00:00Z",
        },
      ],
      uncertainty_reason: "No value was provided for age.",
    },
  ],
  sources: [
    {
      title: "Verified source",
      url: "https://example.gov.in/scheme",
      last_verified_at: "2026-10-22T08:00:00Z",
    },
  ],
  assessed_at: "2026-10-22T08:00:00Z",
  disclaimer: "Preliminary information only.",
  assessment_mode: "saved_profile",
  missing_information: ["Age"],
};

describe("eligibility assessment page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(authService.getCurrentUser).mockResolvedValue({
      id: 7,
      email: "person@example.com",
      full_name: "Sample Person",
      profile_complete: true,
    });
    vi.mocked(schemeService.getSchemeById).mockResolvedValue(scheme);
    vi.mocked(schemeService.assessEligibility).mockResolvedValue(
      savedProfileAssessment,
    );
  });

  it("shows results and uses temporary answers only for the next assessment", async () => {
    render(
      <MemoryRouter
        initialEntries={["/schemes/test-education/eligibility-check"]}
      >
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", {
        name: "Education Support Test Fixture",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/why uncertain: no value was provided for age/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /rule source: verified source/i }),
    ).toHaveAttribute("href", "https://example.gov.in/scheme");

    fireEvent.change(screen.getByLabelText("Age"), {
      target: { value: "22" },
    });
    fireEvent.click(
      screen.getByRole("button", {
        name: "Reassess with temporary answers",
      }),
    );

    expect(schemeService.assessEligibility).toHaveBeenLastCalledWith(
      "test-education",
      { age: 22 },
    );
    expect(
      screen.getByText(/not saved to your profile/i),
    ).toBeInTheDocument();
  });

  it("allows an authenticated user with an incomplete profile to assess", async () => {
    vi.mocked(authService.getCurrentUser).mockResolvedValue({
      id: 7,
      email: "person@example.com",
      full_name: "Sample Person",
      profile_complete: false,
    });

    render(
      <MemoryRouter
        initialEntries={["/schemes/test-education/eligibility-check"]}
      >
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("heading", {
        name: "Education Support Test Fixture",
      }),
    ).toBeInTheDocument();
    expect(schemeService.assessEligibility).toHaveBeenCalledWith(
      "test-education",
    );
  });
});
