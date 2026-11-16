// SignInPage — token-entry gate. Re-pointed 2026-11-16 (findings
// api:2/ui:0): the user enters their secret sign-in token, which is no
// longer the (public) user id. The pages' only side effects are
// useSession().signIn / retryRestore / signOut, so the session module is
// mocked; ApiError is the real class from the api client.
//
// SessionRetryPage (ui:18): when a saved sign-in cannot be checked (no
// response, 5xx, ...) the token is kept and the user gets a retry screen,
// not the sign-in form.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type { SessionNotice } from "../../app/session";
import { SessionRetryPage, SignInPage } from "../SignInPage";

const { signIn, signOut, retryRestore, state } = vi.hoisted(() => ({
  signIn: vi.fn(),
  signOut: vi.fn(),
  retryRestore: vi.fn(),
  state: { notice: null as SessionNotice | null, restoreError: null as string | null },
}));

vi.mock("../../app/session", () => ({
  useSession: () => ({
    session: state.restoreError ? undefined : null,
    signIn,
    signOut,
    selectMatter: vi.fn(),
    refresh: vi.fn(),
    notice: state.notice,
    restoreError: state.restoreError,
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
    signOut.mockReset();
    retryRestore.mockReset();
    state.notice = null;
    state.restoreError = null;
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

  it.each([404, 429])(
    "does not call the token unknown when the server answers %i (only 401 means that)",
    async (status) => {
      signIn.mockRejectedValue(new ApiError(status, "x"));
      render(<SignInPage />);

      typeToken("admin");
      fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

      const banner = await screen.findByRole("alert");
      expect(banner).not.toHaveTextContent(/unknown sign-in token/i);
      expect(banner).toHaveTextContent(/could not reach the lexgraph server/i);
    },
  );

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

  // Re-pointed 2026-11-16 (ui:18): "offers to retry restoring the saved
  // token when the server was unreachable" pinned a "Try again" button on
  // the sign-in form. A kept token no longer lands on the sign-in form at
  // all (that read as being signed out); SessionRetryPage below covers it.
  it("never offers a retry: the sign-in page is only shown when signed out", () => {
    render(<SignInPage />);

    expect(screen.queryByRole("button", { name: /try again|retry/i })).not.toBeInTheDocument();
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

describe("SessionRetryPage", () => {
  beforeEach(() => {
    signOut.mockReset();
    retryRestore.mockReset();
    retryRestore.mockResolvedValue(undefined);
    state.notice = null;
    state.restoreError = "No response from the server.";
  });

  it("says the server could not be reached and that the sign-in is still saved", () => {
    render(<SessionRetryPage />);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(/could not reach the lexgraph server/i);
    expect(alert).toHaveTextContent("No response from the server.");
    expect(screen.getByText(/still saved on this device/i)).toBeInTheDocument();
    // Not the sign-in form: the user does not need their token again.
    expect(screen.queryByLabelText(/sign-in token/i)).not.toBeInTheDocument();
  });

  it("retries on demand and shows that it is retrying", async () => {
    let finish!: () => void;
    retryRestore.mockReturnValue(new Promise<void>((resolve) => (finish = resolve)));
    render(<SessionRetryPage />);

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(retryRestore).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole("button", { name: /retrying/i })).toBeDisabled();
    finish();
    expect(await screen.findByRole("button", { name: "Retry" })).toBeEnabled();
  });

  it("offers signing in with a different token", () => {
    render(<SessionRetryPage />);

    fireEvent.click(screen.getByRole("button", { name: "Sign in with a different token" }));

    expect(signOut).toHaveBeenCalledTimes(1);
  });
});
