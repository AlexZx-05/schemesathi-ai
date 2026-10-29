import { fireEvent, render, screen } from "@testing-library/react";
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
    logout: vi.fn(),
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
  },
}));

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}

describe("application routes", () => {
  beforeEach(() => {
    vi.mocked(authService.getCurrentUser).mockRejectedValue(
      new ApiError("Sign in to continue.", 401),
    );
  });

  it("renders the independent civic-tech landing page", async () => {
    renderAt("/");

    expect(
      await screen.findByRole("heading", {
        name: /discover government benefits that are right for you/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/not an official government service/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: /main navigation/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /schemesathi ai home/i }),
    ).toHaveTextContent("SchemeSathi AI");
    expect(
      screen
        .getByRole("link", { name: /schemesathi ai home/i })
        .querySelector("img"),
    ).toHaveAttribute("src", "/images/Indian.png");
    expect(
      screen.getByText("Your Guide to Government Opportunities"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: /students and a farmer in front of an illustration/i,
      }),
    ).toHaveAttribute("src", "/images/scheme-opportunities-hero.png");
    expect(
      screen.getByRole("searchbox", {
        name: /search scheme records/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /frequently asked questions/i }),
    ).toBeInTheDocument();
  });

  it("shows catalogue review guidance in scheme discovery", async () => {
    renderAt("/schemes");

    expect(
      await screen.findByRole("heading", {
        name: /explore government schemes/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("complementary", { name: /catalogue review notice/i }),
    ).toHaveTextContent(/only records with a reviewed official source/i);
  });

  it("renders a not-found route", () => {
    renderAt("/unknown");

    expect(
      screen.getByRole("heading", { name: /this page isn’t here/i }),
    ).toBeInTheDocument();
  });

  it("opens and closes the mobile navigation accessibly", () => {
    renderAt("/");

    const menuButton = screen.getByRole("button", {
      name: /open navigation menu/i,
    });
    const navigation = screen.getByRole("navigation", {
      name: /main navigation/i,
    });

    expect(menuButton).toHaveAttribute("aria-controls", "main-navigation");
    fireEvent.click(menuButton);

    expect(menuButton).toHaveAttribute("aria-expanded", "true");
    expect(navigation).toHaveClass("site-nav--open");

    fireEvent.click(
      screen.getByRole("button", { name: /close navigation menu/i }),
    );

    expect(
      screen.getByRole("navigation", { name: /main navigation/i }),
    ).not.toHaveClass("site-nav--open");
  });

  it("connects the header account actions to authentication pages", async () => {
    renderAt("/");

    expect(await screen.findByRole("link", { name: "Login" })).toHaveAttribute(
      "href",
      "/login",
    );
    expect(screen.getByRole("link", { name: "Sign Up" })).toHaveAttribute(
      "href",
      "/signup",
    );
  });
});
