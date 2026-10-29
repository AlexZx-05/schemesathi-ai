import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "../src/App";
import { ApiError } from "../src/lib/api";
import { authService } from "../src/lib/auth";

vi.mock("../src/lib/auth", () => ({
  authService: {
    getCurrentUser: vi.fn(),
    register: vi.fn(),
    login: vi.fn(),
    googleLogin: vi.fn(),
    logout: vi.fn(),
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
    getEmailDeliveryStatus: vi.fn(),
  },
}));

const user = {
  id: 1,
  email: "person@example.com",
  full_name: "Sample Person",
  profile_complete: true,
};

const profile = {
  ...user,
  age: null,
  state: "Karnataka",
  district: null,
  area_type: null,
  occupation: "Student",
  occupation_other: null,
  employment_status: null,
  worker_category: null,
  education_level: "Undergraduate",
  qualification: null,
  field_of_study: null,
  years_experience: null,
  preferred_job_roles: [],
  preferred_job_states: [],
  current_student: null,
  annual_income_range: "Prefer not to say",
  household_size: null,
  beneficiary_categories: ["Students"],
  profile_complete: true,
};

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}

describe("authentication and profile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(authService.getCurrentUser).mockRejectedValue(
      new ApiError("Sign in to continue.", 401),
    );
    vi.mocked(authService.getEmailDeliveryStatus).mockResolvedValue({
      development_inbox_available: false,
    });
    vi.mocked(authService.logout).mockResolvedValue(undefined);
  });

  it("redirects a signed-out visitor away from the protected profile", async () => {
    renderAt("/profile");

    expect(
      await screen.findByRole("heading", { name: /sign in to schemesathi/i }),
    ).toBeInTheDocument();
  });

  it("renders the split onboarding wizard with its civic hero image", async () => {
    vi.mocked(authService.getCurrentUser).mockResolvedValue({
      ...user,
      profile_complete: false,
    });
    vi.mocked(authService.getProfile).mockResolvedValue({
      ...profile,
      profile_complete: false,
    });

    renderAt("/onboarding/personal");

    expect(
      await screen.findByRole("heading", { name: "Personal" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: /indian students and family in front of the parliament/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("list", { name: /onboarding progress/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
  });

  it("registers with validated fields and routes to profile onboarding", async () => {
    vi.mocked(authService.register).mockResolvedValue({
      message:
        "If this address can be registered, a verification email will be sent.",
    });
    vi.mocked(authService.getProfile).mockResolvedValue({
      ...profile,
      state: null,
      occupation: null,
      education_level: null,
      annual_income_range: null,
      beneficiary_categories: [],
    });
    renderAt("/register");

    fireEvent.change(screen.getByLabelText("Full name"), {
      target: { value: "Sample Person" },
    });
    fireEvent.change(screen.getByLabelText("Email address"), {
      target: { value: "person@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correct horse battery" },
    });
    fireEvent.change(screen.getByLabelText("Confirm password"), {
      target: { value: "correct horse battery" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign up/i }));

    expect(
      await screen.findByRole("heading", { name: /verify your email/i }),
    ).toBeInTheDocument();
    expect(authService.register).toHaveBeenCalledWith({
      full_name: "Sample Person",
      email: "person@example.com",
      password: "correct horse battery",
    });
  });

  it("reports registration validation errors without calling the API", async () => {
    renderAt("/register");
    fireEvent.click(screen.getByRole("button", { name: /sign up/i }));

    expect(await screen.findByText("Enter your name.")).toBeInTheDocument();
    expect(authService.register).not.toHaveBeenCalled();
  });

  it("shows login failures returned by the authentication service", async () => {
    vi.mocked(authService.login).mockRejectedValue(
      new ApiError("Email or password is incorrect.", 401),
    );
    renderAt("/login");
    fireEvent.change(screen.getByLabelText("Email address"), {
      target: { value: "person@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      await screen.findByText("Email or password is incorrect."),
    ).toBeInTheDocument();
  });

  it("reveals and hides the password without submitting the form", () => {
    renderAt("/login");

    const passwordField = screen.getByLabelText("Password");
    expect(passwordField).toHaveAttribute("type", "password");

    fireEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(passwordField).toHaveAttribute("type", "text");

    fireEvent.click(screen.getByRole("button", { name: "Hide password" }));
    expect(passwordField).toHaveAttribute("type", "password");
    expect(authService.login).not.toHaveBeenCalled();
  });

  it("loads and saves corrected profile information", async () => {
    vi.mocked(authService.getCurrentUser).mockResolvedValue(user);
    vi.mocked(authService.getProfile).mockResolvedValue(profile);
    vi.mocked(authService.updateProfile).mockImplementation(async (input) => ({
      ...profile,
      ...input,
    }));
    renderAt("/profile");

    const nameField = await screen.findByLabelText("Full name");
    expect(screen.getByLabelText(/state or union territory/i)).toHaveValue(
      "Karnataka",
    );
    expect(screen.getByLabelText(/occupation/i)).toHaveValue("Student");
    fireEvent.change(nameField, { target: { value: "Updated Person" } });
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(
      await screen.findByRole("heading", { name: "Family Details" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(
      await screen.findByRole("heading", { name: "Additional Info" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(
      await screen.findByRole("heading", { name: "Job Preferences" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(
      await screen.findByRole("heading", { name: "Review" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /save and complete/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Profile saved.",
    );
    await waitFor(() =>
      expect(authService.updateProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          full_name: "Updated Person",
          state: "Karnataka",
          beneficiary_categories: ["Students"],
        }),
      ),
    );
  });

  it("validates basic details before allowing onboarding to continue", async () => {
    vi.mocked(authService.getCurrentUser).mockResolvedValue(user);
    vi.mocked(authService.getProfile).mockResolvedValue({
      ...profile,
      state: null,
      occupation: null,
      education_level: null,
      annual_income_range: null,
      beneficiary_categories: [],
    });
    renderAt("/profile");

    await screen.findByLabelText("Full name");
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    expect(
      await screen.findByText("Choose your state or territory."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Basic Details" }),
    ).toBeInTheDocument();
  });
});
