"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PUBLIC_API_BASE } from "../../lib/api";

function ConfirmInner() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [status, setStatus] = useState<"pending" | "ok" | "error">("pending");
  const [message, setMessage] = useState("Confirming…");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Missing token.");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${PUBLIC_API_BASE}/auth/confirm?token=${encodeURIComponent(token)}`);
        const body = await res.json();
        if (cancelled) return;
        if (res.ok && body.ok) {
          setStatus("ok");
          setMessage("Email confirmed. Redirecting to login…");
          setTimeout(() => router.push("/login"), 1500);
        } else {
          setStatus("error");
          setMessage(body.detail || body.error || "Confirmation failed");
        }
      } catch (err) {
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Network error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, router]);

  return (
    <div className="space-y-4 sm:space-y-6 max-w-sm mx-auto">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Confirm email</h1>
      </header>
      <div className="card">
        <p className={`text-sm ${status === "ok" ? "text-jade-400" : status === "error" ? "text-rose-400" : "text-ink-400"}`}>
          {message}
        </p>
      </div>
    </div>
  );
}

export default function ConfirmEmailPage() {
  return (
    <Suspense fallback={<div className="card max-w-sm mx-auto">Loading…</div>}>
      <ConfirmInner />
    </Suspense>
  );
}