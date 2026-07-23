"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

/**
 * Client-side guard for route groups. Place as the first child
 * of a layout.tsx wrapping protected routes. Checks localStorage
 * for nakama_token and redirects to /login if missing.
 */
export function RouteGuard({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<"checking" | "ok" | "redirect">("checking");
  const router = useRouter();

  useEffect(() => {
    try {
      const token = localStorage.getItem("nakama_token");
      if (!token) {
        setState("redirect");
        router.replace(
          "/login?redirect=" + encodeURIComponent(window.location.pathname)
        );
        return;
      }
      setState("ok");
    } catch {
      setState("redirect");
      router.replace("/login");
    }
  }, [router]);

  if (state === "checking") {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-48 rounded bg-ink-800" />
        <div className="h-64 w-full rounded bg-ink-800/50" />
      </div>
    );
  }

  if (state === "redirect") {
    return (
      <div className="card text-sm text-ink-400" role="status" aria-live="polite">
        Redirecting to login…
      </div>
    );
  }

  return <>{children}</>;
}
