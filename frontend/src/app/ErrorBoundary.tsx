// Catches render errors so one broken page cannot blank the whole app
// (finding ui:27: an uncaught URIError in routing left #root empty, and a
// reload stayed blank because the hash was unchanged). App wraps the routed
// page in one boundary, inside the shell so navigation keeps working, and
// the whole app in another.

import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

import { navigate } from "./router";

interface Props {
  children: ReactNode;
  /** A caught error is cleared when this changes (e.g. the route changed). */
  resetKey?: string;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("LexGraph could not render this view:", error, info.componentStack);
  }

  componentDidUpdate(previous: Props): void {
    if (this.state.error && previous.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  private backToReviewQueue = (): void => {
    navigate("/review");
    this.setState({ error: null });
  };

  render(): ReactNode {
    if (!this.state.error) return this.props.children;
    return (
      <div className="empty-state error-state" role="alert">
        <p className="empty-state__title">Something went wrong</p>
        <p>This view could not be displayed. Your data is unaffected.</p>
        <div className="error-state__actions">
          <button type="button" className="btn btn--primary" onClick={this.backToReviewQueue}>
            Back to Review Queue
          </button>
          <button
            type="button"
            className="btn btn--secondary"
            onClick={() => window.location.reload()}
          >
            Reload
          </button>
        </div>
      </div>
    );
  }
}
