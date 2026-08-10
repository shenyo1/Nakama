"use client"

import Link from "next/link";

import { useState } from "react";

interface ReviewFormProps {
  source: string;
  slug: string;
  kind: "anime" | "comic" | "novel";
  onSubmitted?: () => void;
}

export function ReviewForm({ source, slug, kind, onSubmitted }: ReviewFormProps) {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (rating < 1 || rating > 5) {
      setError("Please select a rating");
      return;
    }
    if (!body.trim()) {
      setError("Please write a review");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const token = localStorage.getItem("nakama_token");
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/reviews/${encodeURIComponent(source)}/${encodeURIComponent(slug)}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: token ? `Bearer ${token}` : "",
          },
          body: JSON.stringify({ kind, rating, body: body.trim() }),
        }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Error ${res.status}`);
      }
      setSuccess(true);
      setBody("");
      setRating(0);
      onSubmitted?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <div className="card border-emerald-500/30 bg-emerald-500/5 text-sm text-emerald-300">
        ✅ Review submitted! Thank you for sharing.
        <button
          onClick={() => setSuccess(false)}
          className="ml-3 text-sakura-400 hover:underline"
        >
          Write another
        </button>
      </div>
    );
  }

  const token = typeof window !== "undefined" ? localStorage.getItem("nakama_token") : null;
  if (!token) {
    return (
      <div className="card text-sm text-ink-400">
        <Link href="/login" className="text-sakura-400 hover:underline">
          Log in
        </Link>{" "}
        to leave a review.
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="card space-y-3">
      <h3 className="text-sm font-semibold">Write a Review</h3>

      {/* Star rating */}
      <div className="flex items-center gap-1">
        <span className="text-xs text-ink-400 mr-2">Rating:</span>
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => setRating(star)}
            onMouseEnter={() => setHoverRating(star)}
            onMouseLeave={() => setHoverRating(0)}
            className={`text-xl transition-colors ${
              (hoverRating || rating) >= star
                ? "text-amber-400"
                : "text-ink-600 hover:text-amber-400/50"
            }`}
            aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
          >
            ★
          </button>
        ))}
        {rating > 0 && (
          <span className="text-xs text-ink-400 ml-1">{rating}/5</span>
        )}
      </div>

      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Share your thoughts about this title..."
        rows={4}
        maxLength={5000}
        className="w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-500 focus:border-sakura-500 focus:outline-none focus:ring-1 focus:ring-sakura-500"
      />
      <div className="flex items-center justify-between">
        <span className="text-xs text-ink-500">{body.length}/5000</span>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-sakura-600 px-4 py-2 text-sm font-medium text-white hover:bg-sakura-500 disabled:opacity-50 transition-colors"
        >
          {submitting ? "Submitting..." : "Submit Review"}
        </button>
      </div>
      {error && <p className="text-xs text-rose-400">{error}</p>}
    </form>
  );
}
