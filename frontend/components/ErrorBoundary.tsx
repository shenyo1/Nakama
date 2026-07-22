"use client";

import { Component, ReactNode } from "react";

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="card border-sakura-500/40 text-sm text-sakura-200">
          Something went wrong loading this page.
          <details className="mt-2 text-xs text-ink-400">
            <summary>Error details</summary>
            <pre className="mt-2 whitespace-pre-wrap">{this.state.error?.message || "Unknown error"}</pre>
          </details>
        </div>
      );
    }
    return this.props.children;
  }
}
