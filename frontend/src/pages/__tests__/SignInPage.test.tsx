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

  it("fills the input from a demo-account chip and clears any prior error", async () => {
    signIn.mockRejectedValue(new ApiError(401, "unknown user"));
    render(<SignInPage />);

    expect(
      screen.getByText(/demo workspace accounts \(after running the seed\)/i),
    ).toBeInTheDocument();

    // Produce an error first so the chip can clear it.
    typeUserId("nobody");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));
    await screen.findByRole("alert");

    fireEvent.click(screen.getByRole("button", { name: /^reviewer$/i }));

    expect(screen.getByLabelText(/user id/i)).toHaveValue("reviewer");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    // Chips only fill the input — no extra sign-in call.
    expect(signIn).toHaveBeenCalledTimes(1);
  });

  it("offers one chip per demo role", () => {
    render(<SignInPage />);

    for (const role of ["admin", "reviewer", "contributor", "viewer"]) {
      expect(
        screen.getByRole("button", { name: new RegExp(`^${role}$`, "i") }),
      ).toBeInTheDocument();
    }
  });
});
