// SignInPage — token-entry gate. Re-pointed 2026-11-16 (findings
// api:2/ui:0): the user enters their secret sign-in token, which is no
// longer the (public) user id. The page's only side effects are
// useSession().signIn / retryRestore, so the session module is mocked;
// ApiError is the real class from the api client.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type { SessionNotice } from "../../app/session";
import { SignInPage } from "../SignInPage";

const { signIn, retryRestore, state } = vi.hoisted(() => ({
  signIn: vi.fn(),
  retryRestore: vi.fn(),
  state: { notice: null as SessionNotice | null },
}));

vi.mock("../../app/session", () => ({
  useSession: () => ({
    session: null,
    signIn,
    signOut: vi.fn(),
    selectMatter: vi.fn(),
    refresh: vi.fn(),
    notice: state.notice,
    retryRestore,
  }),
}));

function typeToken(value: string) {
  fireEvent.change(screen.getByLabelText(/sign-in token/i), {
    target: { value },
  });
}

describe("SignInPage", () => {
  beforeEach(() => {
    signIn.mockReset();
    signIn.mockResolvedValue(undefined);
    retryRestore.mockReset();
    state.notice = null;
  });

  it("renders the bare token sign-in card without SSO or password fictions", () => {
    render(<SignInPage />);

    expect(screen.getByRole("heading", { name: "LexGraph" })).toBeInTheDocument();
    expect(screen.getByLabelText(/sign-in token/i)).toBeInTheDocument();
    expect(
      screen.getByText(/accounts are provisioned by your administrator/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeInTheDocument();

    // The design's SSO button and password field must not ship.
    expect(screen.queryByText(/company account/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
  });

  it("asks for the sign-in token, masked, and says the user id is not it", () => {
    render(<SignInPage />);

    const input = screen.getByLabelText(/sign-in token/i);
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveAccessibleDescription(/your user id is not your sign-in token/i);
    expect(screen.queryByLabelText(/user id/i)).not.toBeInTheDocument();
  });

  it("keeps the submit button disabled while the token is empty or blank", () => {
    render(<SignInPage />);

    const button = screen.getByRole("button", { name: /^sign in$/i });
    expect(button).toBeDisabled();

    typeToken("   ");
    expect(button).toBeDisabled();
    expect(signIn).not.toHaveBeenCalled();
  });

  it("signs in with the trimmed token on submit", async () => {
    render(<SignInPage />);

    typeToken("  reviewer  ");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    await waitFor(() => expect(signIn).toHaveBeenCalledWith("reviewer"));
    expect(signIn).toHaveBeenCalledTimes(1);
  });

  it("disables the submit button while sign-in is pending", async () => {
    signIn.mockImplementation(() => new Promise<void>(() => {}));
    render(<SignInPage />);

    typeToken("someone");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    const pendingButton = await screen.findByRole("button", {
      name: /signing in/i,
    });
    expect(pendingButton).toBeDisabled();
  });

  it("shows the unknown-token error banner on ApiError and re-enables the form", async () => {
    signIn.mockRejectedValue(new ApiError(401, "unknown sign-in token"));
    render(<SignInPage />);

    typeToken("nobody");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent(/unknown sign-in token/i);
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeEnabled();
  });

  it("shows a connectivity message when sign-in fails without an API response", async () => {
    signIn.mockRejectedValue(new TypeError("fetch failed"));
    render(<SignInPage />);

    typeToken("admin");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent(/could not reach the lexgraph server/i);
  });

  it("treats a 5xx response as connectivity trouble, not an unknown token", async () => {
    signIn.mockRejectedValue(new ApiError(502, "Bad Gateway"));
    render(<SignInPage />);

    typeToken("admin");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent(/could not reach the lexgraph server/i);
  });

  it("explains a rejected saved token (e.g. rotated) without a retry button", () => {
    state.notice = { kind: "token_rejected", message: "Your saved sign-in token is no longer valid." };
    render(<SignInPage />);

    expect(screen.getByRole("status")).toHaveTextContent(/no longer valid/i);
    expect(screen.queryByRole("button", { name: /try again/i })).not.toBeInTheDocument();
  });

  it("offers to retry restoring the saved token when the server was unreachable", () => {
    state.notice = { kind: "server_unreachable", message: "Could not reach the LexGraph server." };
    render(<SignInPage />);

    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(retryRestore).toHaveBeenCalledTimes(1);
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
    expect(screen.getByLabelText(/sign-in token/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeInTheDocument();
  });
});
