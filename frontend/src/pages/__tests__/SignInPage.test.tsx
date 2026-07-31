// SignInPage — token-entry gate (bearer token IS the user id).
// The page's only side effect is useSession().signIn, so the session
// module is mocked; ApiError is the real class from the api client.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import { SignInPage } from "../SignInPage";

const { signIn } = vi.hoisted(() => ({ signIn: vi.fn() }));

vi.mock("../../app/session", () => ({
  useSession: () => ({
    session: null,
    signIn,
    signOut: vi.fn(),
    selectMatter: vi.fn(),
    refresh: vi.fn(),
  }),
}));

function typeUserId(value: string) {
  fireEvent.change(screen.getByLabelText(/user id/i), {
    target: { value },
  });
}

describe("SignInPage", () => {
  beforeEach(() => {
    signIn.mockReset();
    signIn.mockResolvedValue(undefined);
  });

  it("renders the bare token sign-in card without SSO or password fictions", () => {
    render(<SignInPage />);

    expect(screen.getByRole("heading", { name: "LexGraph" })).toBeInTheDocument();
    expect(screen.getByLabelText(/user id/i)).toBeInTheDocument();
    expect(
      screen.getByText(/accounts are provisioned by your administrator/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeInTheDocument();

    // The design's SSO button and password field must not ship.
    expect(screen.queryByText(/company account/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
  });

  it("keeps the submit button disabled while the user ID is empty or blank", () => {
    render(<SignInPage />);

    const button = screen.getByRole("button", { name: /^sign in$/i });
    expect(button).toBeDisabled();

    typeUserId("   ");
    expect(button).toBeDisabled();
    expect(signIn).not.toHaveBeenCalled();
  });

  it("signs in with the trimmed user ID on submit", async () => {
    render(<SignInPage />);

    typeUserId("  reviewer  ");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    await waitFor(() => expect(signIn).toHaveBeenCalledWith("reviewer"));
    expect(signIn).toHaveBeenCalledTimes(1);
  });

  it("disables the submit button while sign-in is pending", async () => {
    signIn.mockImplementation(() => new Promise<void>(() => {}));
    render(<SignInPage />);

    typeUserId("someone");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    const pendingButton = await screen.findByRole("button", {
      name: /signing in/i,
    });
    expect(pendingButton).toBeDisabled();
  });

  it("shows the unknown-user error banner on ApiError and re-enables the form", async () => {
    signIn.mockRejectedValue(new ApiError(401, "unknown user"));
    render(<SignInPage />);

    typeUserId("nobody");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent(/unknown user id/i);
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeEnabled();
  });

  it("shows a connectivity message when sign-in fails without an API response", async () => {
    signIn.mockRejectedValue(new TypeError("fetch failed"));
    render(<SignInPage />);

    typeUserId("admin");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent(/could not reach the lexgraph server/i);
  });

  it("treats a 5xx response as connectivity trouble, not an unknown user", async () => {
    signIn.mockRejectedValue(new ApiError(502, "Bad Gateway"));
    render(<SignInPage />);

    typeUserId("admin");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent(/could not reach the lexgraph server/i);
  });

  // Re-pointed for sprint 2026-07-31-admin-provisioning, gate G3 ("no
  // mockup data in the app"): the two tests this replaced
  // ("fills the input from a demo-account chip ..." and "offers one chip
  // per demo role") asserted the hardcoded demo-account quick-fill chips
  // EXISTED. That fixture is being removed — accounts are provisioned by
  // an admin (bootstrap CLI + Users API), not hardcoded in the sign-in
  // page — so this is now a RED test pinning their ABSENCE instead.
  it("does not render the hardcoded demo-account quick-fill chips (G3)", () => {
    render(<SignInPage />);

    expect(
      screen.queryByText(/demo workspace accounts/i),
    ).not.toBeInTheDocument();
    for (const role of ["admin", "reviewer", "contributor", "viewer"]) {
      expect(
        screen.queryByRole("button", { name: new RegExp(`^${role}$`, "i") }),
      ).not.toBeInTheDocument();
    }

    // The real sign-in surface must still be there.
    expect(screen.getByLabelText(/user id/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeInTheDocument();
  });
});
