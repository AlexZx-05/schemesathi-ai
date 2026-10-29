import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "../src/App";
import { ApiError } from "../src/lib/api";
import { authService } from "../src/lib/auth";
import { schemeService } from "../src/lib/schemes/service";
import type { Scheme } from "../src/lib/schemes/types";
import { guidanceService } from "../src/lib/guidance";

const verifiedSchemes: Scheme[] = [
  {
    id: "test-education",
    name: "Education Support Test Fixture",
    shortDescription: "Test record for education search.",
    category: "Education",
    beneficiaries: ["Students"],
    governmentLevel: "Central",
    keywords: ["student", "education"],
    benefits: ["Test benefit."],
    eligibilityCriteria: ["Test criterion."],
    requiredDocuments: ["Test document."],
    applicationProcedure: ["Test step."],
    officialSource: "https://official.gov.in/education",
    lastVerifiedDate: "2026-10-25",
    dataStatus: "verified",
    sources: [
      {
        url: "https://official.gov.in/education",
        title: "Official education source",
        status: "verified",
        lastVerifiedAt: "2026-10-25T00:00:00Z",
      },
    ],
  },
  {
    id: "test-agriculture",
    name: "Agriculture Support Test Fixture",
    shortDescription: "Test record for farmer search.",
    category: "Agriculture",
    beneficiaries: ["Farmers"],
    governmentLevel: "State",
    keywords: ["farmer", "agriculture"],
    benefits: ["Test benefit."],
    eligibilityCriteria: ["Test criterion."],
    requiredDocuments: ["Test document."],
    applicationProcedure: ["Test step."],
    officialSource: "https://official.gov.in/agriculture",
    lastVerifiedDate: "2026-10-25",
    dataStatus: "verified",
  },
  {
    id: "test-health",
    name: "Community Health Support Test Fixture",
    shortDescription: "Test record for catalogue sorting.",
    category: "Healthcare",
    beneficiaries: ["Families"],
    governmentLevel: "Central",
    keywords: ["health", "family"],
    benefits: ["Test benefit."],
    eligibilityCriteria: ["Test criterion."],
    requiredDocuments: ["Test document."],
    applicationProcedure: ["Test step."],
    officialSource: "https://official.gov.in/health",
    lastVerifiedDate: "2026-10-25",
    dataStatus: "verified",
  },
];

vi.mock("../src/lib/schemes/service", () => ({
  schemeService: {
    getSchemes: vi.fn(),
    getSchemeById: vi.fn(),
    assessEligibility: vi.fn(),
    getRecommendations: vi.fn(),
    getDashboardSummary: vi.fn(),
  },
}));

vi.mock("../src/lib/auth", () => ({
  authService: {
    getCurrentUser: vi.fn(),
  },
}));

vi.mock("../src/lib/guidance", () => ({
  guidanceService: {
    listSaved: vi.fn(),
    save: vi.fn(),
    unsave: vi.fn(),
  },
}));

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}

describe("scheme discovery", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.mocked(schemeService.getSchemes).mockResolvedValue(verifiedSchemes);
    vi.mocked(schemeService.getSchemeById).mockImplementation(
      async (schemeId) =>
        verifiedSchemes.find((scheme) => scheme.id === schemeId) ?? null,
    );
    vi.mocked(authService.getCurrentUser).mockRejectedValue(
      new ApiError("Sign in to continue.", 401),
    );
    vi.mocked(guidanceService.listSaved).mockResolvedValue([]);
  });

  it("renders only source-reviewed catalogue records", async () => {
    renderAt("/schemes");

    expect(
      await screen.findByRole("heading", {
        name: /explore government schemes/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("complementary", { name: /catalogue review notice/i }),
    ).toHaveTextContent(/only records with a reviewed official source/i);
    expect(
      screen.getByRole("heading", {
        name: /education support test fixture/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Verified source")).toHaveLength(3);
  });

  it("searches names, descriptions, and keywords", async () => {
    renderAt("/schemes");
    await screen.findByRole("heading", { name: /explore government schemes/i });

    fireEvent.change(
      screen.getByRole("searchbox", {
        name: /search scheme names, topics, and beneficiaries/i,
      }),
      { target: { value: "farmer" } },
    );

    expect(
      screen.getByRole("heading", {
        name: /agriculture support test fixture/i,
      }),
    ).toBeInTheDocument();
    expect(document.querySelector(".results-summary p")).toHaveTextContent(
      "1 scheme shown",
    );
  });

  it("combines category, beneficiary, level, and search filters", async () => {
    renderAt("/schemes");
    await screen.findByRole("heading", { name: /explore government schemes/i });

    fireEvent.change(
      screen.getByRole("searchbox", {
        name: /search scheme names, topics, and beneficiaries/i,
      }),
      { target: { value: "student" } },
    );
    fireEvent.change(screen.getByLabelText("Category"), {
      target: { value: "Education" },
    });
    fireEvent.change(screen.getByLabelText("Beneficiary"), {
      target: { value: "Students" },
    });
    fireEvent.change(screen.getByLabelText("Government level"), {
      target: { value: "Central" },
    });

    expect(
      screen.getByRole("heading", {
        name: /education support test fixture/i,
      }),
    ).toBeInTheDocument();
    expect(document.querySelector(".results-summary p")).toHaveTextContent(
      "1 scheme shown",
    );
  });

  it("sorts matching records by name", async () => {
    renderAt("/schemes");
    await screen.findByRole("heading", { name: /explore government schemes/i });

    fireEvent.change(screen.getByLabelText("Sort by"), {
      target: { value: "name-asc" },
    });

    const cards = screen.getAllByRole("article");
    expect(
      within(cards[0]).getByRole("heading", { level: 2 }),
    ).toHaveTextContent("Agriculture Support Test Fixture");
  });

  it("saves and unsaves a scheme through the signed-in API", async () => {
    vi.mocked(authService.getCurrentUser).mockResolvedValue({
      id: 2,
      email: "person@example.com",
      full_name: "Sample Person",
      profile_complete: true,
      is_admin: false,
    });
    vi.mocked(guidanceService.save).mockResolvedValue({
      id: 11,
      scheme_id: "test-education",
      scheme_name: "Education Support Test Fixture",
      scheme_status: "unknown",
      verification_status: "verified",
      last_verified_at: "2026-10-25T00:00:00Z",
      guidance_available: true,
      availability_notice: null,
      saved_at: "2026-10-23T10:00:00Z",
    });
    vi.mocked(guidanceService.unsave).mockResolvedValue(undefined);
    renderAt("/schemes");
    await screen.findByRole("heading", { name: /explore government schemes/i });
    await screen.findByRole("heading", {
      name: /education support test fixture/i,
    });

    const saveButton = screen.getByRole("button", {
      name: /save education support test fixture/i,
    });
    fireEvent.click(saveButton);

    await waitFor(() =>
      expect(saveButton).toHaveAttribute("aria-pressed", "true"),
    );
    expect(guidanceService.save).toHaveBeenCalledWith("test-education");
    fireEvent.click(saveButton);
    await waitFor(() =>
      expect(guidanceService.unsave).toHaveBeenCalledWith("test-education"),
    );
    await waitFor(() =>
      expect(saveButton).toHaveAttribute("aria-pressed", "false"),
    );
  });

  it("renders the details for a valid scheme id", async () => {
    renderAt("/schemes/test-education");

    expect(
      await screen.findByRole("heading", {
        name: /education support test fixture/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /eligibility criteria/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /official education source/i }),
    ).toHaveAttribute("href", "https://official.gov.in/education");
  });

  it("explains when no reviewed schemes have been published", async () => {
    vi.mocked(schemeService.getSchemes).mockResolvedValueOnce([]);
    renderAt("/schemes");

    expect(
      await screen.findByRole("heading", {
        name: /no reviewed schemes are published yet/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /visit national portal of india/i }),
    ).toHaveAttribute("href", "https://www.india.gov.in/");
  });

  it("shows a useful message for an unknown scheme id", async () => {
    renderAt("/schemes/not-a-real-record");

    expect(
      await screen.findByRole("heading", { name: /scheme record not found/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /browse schemes/i }),
    ).toHaveAttribute("href", "/schemes");
  });

  it("shows a retryable error state when the catalogue service fails", async () => {
    vi.mocked(schemeService.getSchemes).mockRejectedValueOnce(
      new Error("Catalogue is unavailable."),
    );
    renderAt("/schemes");

    expect(
      await screen.findByRole("heading", {
        name: /we couldn’t load scheme records/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Catalogue is unavailable.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /try again/i }),
    ).toBeInTheDocument();
  });

  it("routes landing-page searches to filtered results", async () => {
    renderAt("/");

    const searchBox = await screen.findByRole("searchbox", {
      name: /search scheme records/i,
    });
    fireEvent.change(searchBox, {
      target: { value: "farmer" },
    });
    fireEvent.click(screen.getByRole("button", { name: /search schemes/i }));

    expect(
      await screen.findByRole("heading", {
        name: /explore government schemes/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("searchbox", {
        name: /search scheme names, topics, and beneficiaries/i,
      }),
    ).toHaveValue("farmer");
    expect(document.querySelector(".results-summary p")).toHaveTextContent(
      "1 scheme shown",
    );
  });
});
