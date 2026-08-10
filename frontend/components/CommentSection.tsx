"use client"

import Link from "next/link";

import { useEffect, useState } from "react";

interface Comment {
  id: number;
  user_id: number;
  username: string;
  source: string;
  slug: string;
  kind: string;
  body: string;
  parent_id: number | null;
  created_at: string;
  replies: Comment[];
}

interface CommentSectionProps {
  source: string;
  slug: string;
  kind?: "anime" | "comic" | "novel";
}

export function CommentSection({ source, slug, kind }: CommentSectionProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newComment, setNewComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [replyingTo, setReplyingTo] = useState<number | null>(null);
  const [replyText, setReplyText] = useState("");

  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  async function loadComments() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (kind) params.set("kind", kind);
      const res = await fetch(
        `${apiBase}/comments/${encodeURIComponent(source)}/${encodeURIComponent(slug)}?${params}`
      );
      if (res.ok) {
        const data = await res.json();
        setComments(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadComments();
  }, [source, slug, kind]);

  async function handlePost(e: React.FormEvent) {
    e.preventDefault();
    if (!newComment.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      const token = localStorage.getItem("nakama_token");
      const res = await fetch(
        `${apiBase}/comments/${encodeURIComponent(source)}/${encodeURIComponent(slug)}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: token ? `Bearer ${token}` : "",
          },
          body: JSON.stringify({ kind: kind || "comic", body: newComment.trim() }),
        }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Error ${res.status}`);
      }
      setNewComment("");
      loadComments();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReply(parentId: number) {
    if (!replyText.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      const token = localStorage.getItem("nakama_token");
      const res = await fetch(
        `${apiBase}/comments/${encodeURIComponent(source)}/${encodeURIComponent(slug)}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: token ? `Bearer ${token}` : "",
          },
          body: JSON.stringify({
            kind: kind || "comic",
            body: replyText.trim(),
            parent_id: parentId,
          }),
        }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Error ${res.status}`);
      }
      setReplyText("");
      setReplyingTo(null);
      loadComments();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  const token = typeof window !== "undefined" ? localStorage.getItem("nakama_token") : null;

  if (loading) {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-4 w-20 bg-ink-800 rounded" />
        <div className="card">
          <div className="h-3 w-full bg-ink-800 rounded mb-2" />
          <div className="h-3 w-2/3 bg-ink-800 rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">
        Comments {comments.length > 0 && `(${comments.length})`}
      </h3>

      {/* New comment form */}
      {token ? (
        <form onSubmit={handlePost} className="card space-y-2">
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Add a comment..."
            rows={3}
            maxLength={3000}
            className="w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-500 focus:border-sakura-500 focus:outline-none focus:ring-1 focus:ring-sakura-500"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-ink-500">{newComment.length}/3000</span>
            <button
              type="submit"
              disabled={submitting || !newComment.trim()}
              className="rounded-md bg-sakura-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sakura-500 disabled:opacity-50 transition-colors"
            >
              {submitting ? "Posting..." : "Post Comment"}
            </button>
          </div>
        </form>
      ) : (
        <div className="card text-sm text-ink-400">
          <Link href="/login" className="text-sakura-400 hover:underline">
            Log in
          </Link>{" "}
          to join the discussion.
        </div>
      )}

      {error && <p className="text-xs text-rose-400">{error}</p>}

      {/* Comments list */}
      {comments.length === 0 ? (
        <p className="text-sm text-ink-400">No comments yet.</p>
      ) : (
        <div className="space-y-3">
          {comments.map((c) => (
            <CommentItem
              key={c.id}
              comment={c}
              replyingTo={replyingTo}
              replyText={replyText}
              setReplyText={setReplyText}
              onReply={setReplyingTo}
              onSubmitReply={handleReply}
              submitting={submitting}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CommentItem({
  comment,
  replyingTo,
  replyText,
  setReplyText,
  onReply,
  onSubmitReply,
  submitting,
}: {
  comment: Comment;
  replyingTo: number | null;
  replyText: string;
  setReplyText: (v: string) => void;
  onReply: (id: number | null) => void;
  onSubmitReply: (parentId: number) => Promise<void>;
  submitting: boolean;
}) {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm font-medium">{comment.username || `User #${comment.user_id}`}</span>
        <time className="text-xs text-ink-500" dateTime={comment.created_at}>
          {new Date(comment.created_at).toLocaleDateString()}
        </time>
      </div>
      <p className="text-sm text-ink-200 leading-relaxed whitespace-pre-wrap">{comment.body}</p>

      <button
        onClick={() => onReply(replyingTo === comment.id ? null : comment.id)}
        className="mt-2 text-xs text-sakura-400 hover:underline"
      >
        {replyingTo === comment.id ? "Cancel" : "Reply"}
      </button>

      {/* Reply form */}
      {replyingTo === comment.id && (
        <div className="mt-2 space-y-2">
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Write a reply..."
            rows={2}
            maxLength={3000}
            className="w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-1.5 text-xs text-ink-100 placeholder:text-ink-500 focus:border-sakura-500 focus:outline-none focus:ring-1 focus:ring-sakura-500"
          />
          <button
            onClick={() => onSubmitReply(comment.id)}
            disabled={submitting || !replyText.trim()}
            className="rounded-md bg-ink-700 px-3 py-1 text-xs font-medium text-ink-100 hover:bg-ink-600 disabled:opacity-50 transition-colors"
          >
            {submitting ? "Posting..." : "Post Reply"}
          </button>
        </div>
      )}

      {/* Nested replies */}
      {comment.replies?.length > 0 && (
        <div className="mt-3 ml-4 pl-3 border-l border-ink-700 space-y-2">
          {comment.replies.map((r) => (
            <div key={r.id}>
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-xs font-medium">{r.username || `User #${r.user_id}`}</span>
                <time className="text-[10px] text-ink-500" dateTime={r.created_at}>
                  {new Date(r.created_at).toLocaleDateString()}
                </time>
              </div>
              <p className="text-xs text-ink-300 leading-relaxed">{r.body}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
