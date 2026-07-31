import { AppShell } from "./app/AppShell";
import { matchPath, useHashLocation } from "./app/router";
import { SessionProvider, useSession } from "./app/session";
import { AdminPage } from "./pages/AdminPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { AssertionDetailPage } from "./pages/AssertionDetailPage";
import { ContestedPage } from "./pages/ContestedPage";
import { KnowledgeBasePage } from "./pages/KnowledgeBasePage";
import { ProfilePage } from "./pages/ProfilePage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { SignInPage } from "./pages/SignInPage";
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
  return (
    <div className="empty-state">
      <p className="empty-state__title">No matter access</p>
      <p>
        Your account is not a member of any matter yet. Ask a matter admin to add
        you, or run the demo seed script (see README).
      </p>
    </div>
  );
}

function AppRoutes() {
  const { session } = useSession();
  const location = useHashLocation();

  if (session === undefined) {
    return <div className="loading">Restoring session…</div>;
  }
  if (session === null) {
    return <SignInPage />;
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

  return <AppShell>{content}</AppShell>;
}

export default function App() {
  return (
    <SessionProvider>
      <AppRoutes />
    </SessionProvider>
  );
}
