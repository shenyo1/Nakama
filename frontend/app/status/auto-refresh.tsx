"use client";
import { useEffect } from "react";

/** Auto-refresh the status page every 60s (passive) or 120s (probe). */
export default function AutoRefresh({ probe }: { probe?: boolean }) {
  useEffect(() => {
    const interval = setInterval(() => {
      // Soft reload preserves the current probe flag from the URL.
      window.location.reload();
    }, probe ? 120_000 : 60_000);
    return () => clearInterval(interval);
  }, [probe]);
  return null;
}
