"use client";

import { Component, ReactNode } from "react";
import { PUBLIC_API_BASE } from "../lib/api";

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: { componentStack?: string }) {
    // Report to the backend's /errors endpoint so the operator can see it
    // in /admin/errors or get a Telegram alert on critical severity.
    try {
      void fetch(`${PUBLIC_API_BASE}/errors`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: error.message,
          stack: info.componentStack?.slice(0, 4000) || null,
          source: "ErrorBoundary",
          severity: "error",
          extra: { name: error.name },
        }),
        keepalive: true,
      });
    } catch {
      // Never let error reporting itself break the page.
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="card border-sakura-500/40 text-sm text-sakura-200"
          role="alert"
          aria-live="assertive"
        >
          Something went wrong loading this page.
          <details className="mt-2 text-xs text-ink-400">
            <summary>Error details</summary>
            <pre className="mt-2 whitespace-pre-wrap">
              {this.state.error?.message || "Unknown error"}
            </pre>
          </details>
        </div>
      );
    }
    return this.props.children;
  }
}
