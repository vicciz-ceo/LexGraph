import { AppShell } from "./app/AppShell";
import { ErrorBoundary } from "./app/ErrorBoundary";
import { IssuedTokenCallout } from "./app/IssuedTokenCallout";
import { matchPath, useHashLocation } from "./app/router";
import { SessionProvider, useSession } from "./app/session";
import { AdminPage } from "./pages/AdminPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { AssertionDetailPage } from "./pages/AssertionDetailPage";
import { ContestedPage } from "./pages/ContestedPage";
import { KnowledgeBasePage } from "./pages/KnowledgeBasePage";
import { ProfilePage } from "./pages/ProfilePage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { SessionRetryPage, SignInPage } from "./pages/SignInPage";
import { SuggestAssertionPage } from "./pages/SuggestAssertionPage";

function NotAuthorized() {
  return (
    <div className="empty-state">
      <p className="empty-state__title">Not authorized</p>
      <p>This area requires the admin role on the current matter.</p>
    </div>
  );
}

function NoMatter() {
  // Accounts and access are provisioned in-app by a matter admin; the demo
  // seed is a local-testing tool that cannot help here.
  return (
    <div className="empty-state">
      <p className="empty-state__title">No matter access</p>
      <p>
        Your account is not a member of any matter yet. Ask a matter admin to add
        you.
      </p>
    </div>
  );
}

function AppRoutes() {
  const { session, restoreError, issuedOwnToken, acknowledgeIssuedOwnToken } = useSession();
  const location = useHashLocation();

  if (session === undefined) {
    // A saved sign-in that could not be checked keeps its token (ui:18).
    return restoreError ? <SessionRetryPage /> : <div className="loading">Restoring session…</div>;
  }
  if (session === null) {
    // Signed out (here or in another tab) before saving the new token of
    // your own rotation: it is not used, but still shown, until Done, as it
    // is the only one that signs in as you now (review identity:2).
    return (
      <SignInPage>
        {issuedOwnToken && (
          <IssuedTokenCallout
            key={issuedOwnToken.sign_in_token}
            account={issuedOwnToken}
            reason="rotated"
            self
            signedOut
            onDone={() => acknowledgeIssuedOwnToken?.()}
          />
        )}
      </SignInPage>
    );
  }

  let content;
  if (!session.currentMatter) {
    content = <NoMatter />;
  } else {
    const detailParams = matchPath("/assertions/:id", location.path);
    if (detailParams) {
      content = <AssertionDetailPage assertionId={detailParams.id} />;
    } else {
      switch (location.path) {
        case "/":
        case "/review":
          content = <ReviewQueuePage />;
          break;
        case "/knowledge":
          content = <KnowledgeBasePage />;
          break;
        case "/suggest":
          content = <SuggestAssertionPage />;
          break;
        case "/contested":
          content = <ContestedPage />;
          break;
        case "/analytics":
          content = <AnalyticsPage />;
          break;
        case "/admin":
          content = session.role === "admin" ? <AdminPage /> : <NotAuthorized />;
          break;
        case "/profile":
          content = <ProfilePage />;
          break;
        default:
          content = <ReviewQueuePage />;
      }
    }
  }

  // A page that fails to render keeps the shell (and its navigation); moving
  // to another route clears the error (ui:27).
  return (
    <AppShell>
      <ErrorBoundary resetKey={`${location.path}?${location.query.toString()}`}>
        {content}
      </ErrorBoundary>
    </AppShell>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <SessionProvider>
        <AppRoutes />
      </SessionProvider>
    </ErrorBoundary>
  );
}
