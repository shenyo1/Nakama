"use client";

import { useEffect, useState } from "react";
import { PUBLIC_API_BASE } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CreatorProfile {
  id: number;
  user_id: number;
  display_name: string;
  bio: string | null;
  avatar_url: string | null;
  social_links: Record<string, string>;
  follower_count: number;
  total_views: number;
  verified: boolean;
}

interface Series {
  id: number;
  creator_id: number;
  title: string;
  description: string | null;
  kind: string;
  cover_image: string | null;
  status: string;
  chapter_count: number;
  total_views: number;
  published: boolean;
  created_at: string;
  updated_at: string;
}

interface Chapter {
  id: number;
  series_id: number;
  title: string;
  chapter_number: number;
  content: string;
  content_format: string;
  word_count: number;
  views: number;
  published: boolean;
  created_at: string;
  updated_at: string;
}

interface DashboardData {
  profile: CreatorProfile;
  series_count: number;
  total_chapters: number;
  total_views: number;
  total_followers: number;
  revenue_estimate: number;
  recent_series: Series[];
  top_chapters: Chapter[];
}

// ---------------------------------------------------------------------------
// Auth helper
// ---------------------------------------------------------------------------

function authHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("nakama_token") : null;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${PUBLIC_API_BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Tab definitions
// ---------------------------------------------------------------------------

type Tab = "dashboard" | "register" | "series" | "editor";

export default function CreatorPage() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [profile, setProfile] = useState<CreatorProfile | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [seriesList, setSeriesList] = useState<Series[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load profile + dashboard
  useEffect(() => {
    loadProfile();
  }, []);

  async function loadProfile() {
    setLoading(true);
    setError(null);
    try {
      const p = await apiFetch<CreatorProfile>("/creator/profile");
      setProfile(p);
      // Only load dashboard if profile exists
      const d = await apiFetch<DashboardData>("/creator/dashboard");
      setDashboard(d);
      setSeriesList(d.recent_series);
    } catch (e: any) {
      if (e.message?.includes("404")) {
        setProfile(null);
        setTab("register");
      } else {
        setError(e.message || String(e));
      }
    } finally {
      setLoading(false);
    }
  }

  async function loadSeries() {
    try {
      const s = await apiFetch<Series[]>("/creator/series?limit=50");
      setSeriesList(s);
    } catch (e: any) {
      setError(e.message || String(e));
    }
  }

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-48 rounded bg-ink-800" />
        <div className="h-64 w-full rounded bg-ink-800/50" />
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold sm:text-3xl">Creator Portal</h1>
        <p className="text-sm text-ink-400">
          {profile
            ? `Welcome, ${profile.display_name}! Manage your content here.`
            : "Register as a creator to publish your work."}
        </p>
      </header>

      {error && (
        <div className="card border-sakura-500/30 bg-sakura-500/5 text-sm text-sakura-200">
          {error}
          <button
            onClick={() => { setError(null); loadProfile(); }}
            className="ml-4 underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Tab navigation */}
      {profile && (
        <nav className="flex gap-1 border-b border-ink-700/50 pb-2">
          {(["dashboard", "series", "editor"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-md px-3 py-1.5 text-sm capitalize transition ${
                tab === t
                  ? "bg-sakura-500/20 text-sakura-300"
                  : "text-ink-400 hover:text-ink-200"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      )}

      {/* Tab content */}
      {!profile && tab === "register" && (
        <RegisterForm onRegistered={loadProfile} />
      )}
      {profile && tab === "dashboard" && dashboard && (
        <DashboardView data={dashboard} />
      )}
      {profile && tab === "series" && (
        <SeriesManager
          series={seriesList}
          onRefresh={loadSeries}
          apiFetch={apiFetch}
        />
      )}
      {profile && tab === "editor" && (
        <ChapterEditor
          series={seriesList}
          apiFetch={apiFetch}
          onRefresh={loadSeries}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Register Form
// ---------------------------------------------------------------------------

function RegisterForm({ onRegistered }: { onRegistered: () => void }) {
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await apiFetch("/creator/register", {
        method: "POST",
        body: JSON.stringify({
          display_name: displayName,
          bio: bio || null,
          social_links: {},
        }),
      });
      setSuccess(true);
      setTimeout(onRegistered, 1000);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card max-w-lg space-y-4">
      <h2 className="text-lg font-semibold">Become a Creator</h2>
      <p className="text-sm text-ink-400">
        Set up your creator profile to start publishing stories, comics, and art.
      </p>

      {error && <div className="text-sm text-sakura-300">{error}</div>}
      {success && <div className="text-sm text-emerald-300">Profile created! Redirecting...</div>}

      <label className="block">
        <span className="text-sm text-ink-300">Display Name *</span>
        <input
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          required
          minLength={1}
          maxLength={128}
          className="mt-1 w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-600 focus:border-sakura-500 focus:outline-none"
          placeholder="Your creator name"
        />
      </label>

      <label className="block">
        <span className="text-sm text-ink-300">Bio</span>
        <textarea
          value={bio}
          onChange={(e) => setBio(e.target.value)}
          maxLength={2000}
          rows={3}
          className="mt-1 w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-600 focus:border-sakura-500 focus:outline-none"
          placeholder="Tell readers about yourself..."
        />
      </label>

      <button
        type="submit"
        disabled={submitting || !displayName}
        className="rounded-md bg-sakura-600 px-4 py-2 text-sm font-medium text-white hover:bg-sakura-500 disabled:opacity-50"
      >
        {submitting ? "Registering..." : "Register as Creator"}
      </button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Dashboard View
// ---------------------------------------------------------------------------

function DashboardView({ data }: { data: DashboardData }) {
  const p = data.profile;
  return (
    <div className="space-y-6">
      {/* Stats cards */}
      <section className="grid gap-2 grid-cols-2 sm:gap-3 lg:grid-cols-4">
        <MiniMetric label="Series" value={String(data.series_count)} />
        <MiniMetric label="Chapters" value={String(data.total_chapters)} />
        <MiniMetric label="Total Views" value={formatNumber(data.total_views)} />
        <MiniMetric label="Followers" value={formatNumber(data.total_followers)} />
        <MiniMetric
          label="Est. Revenue"
          value={`$${data.revenue_estimate.toFixed(2)}`}
          sub="CPM-based estimate"
        />
        <MiniMetric
          label="Verified"
          value={p.verified ? "Yes ✓" : "No"}
          alert={!p.verified}
        />
      </section>

      {/* Profile card */}
      <section className="card">
        <div className="flex items-start gap-4">
          <div className="h-16 w-16 rounded-full bg-ink-700 flex items-center justify-center text-2xl text-ink-400 shrink-0">
            {p.avatar_url ? (
              <img src={p.avatar_url} alt="" className="h-full w-full rounded-full object-cover" />
            ) : (
              p.display_name[0]?.toUpperCase() || "?"
            )}
          </div>
          <div className="min-w-0">
            <h2 className="text-lg font-semibold">{p.display_name}</h2>
            {p.bio && <p className="mt-1 text-sm text-ink-400">{p.bio}</p>}
            {Object.keys(p.social_links).length > 0 && (
              <div className="mt-2 flex gap-2 text-xs">
                {Object.entries(p.social_links).map(([k, v]) => (
                  <a key={k} href={v} target="_blank" rel="noreferrer"
                     className="text-sakura-400 hover:underline">
                    {k}
                  </a>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Recent series */}
      {data.recent_series.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold">Recent Series</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.recent_series.map((s) => (
              <div key={s.id} className="card flex flex-col">
                <div className="flex items-start gap-3">
                  {s.cover_image ? (
                    <img src={s.cover_image} alt="" className="h-14 w-10 rounded object-cover" />
                  ) : (
                    <div className="h-14 w-10 rounded bg-ink-700 flex items-center justify-center text-xs text-ink-500 shrink-0">
                      {s.kind}
                    </div>
                  )}
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold truncate">{s.title}</h3>
                    <p className="text-xs text-ink-400">
                      {s.chapter_count} chapters · {formatNumber(s.total_views)} views
                    </p>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                      s.published ? "bg-emerald-500/20 text-emerald-300" : "bg-amber-500/20 text-amber-300"
                    }`}>
                      {s.published ? "published" : "draft"}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Top chapters */}
      {data.top_chapters.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold">Top Chapters</h2>
          <div className="space-y-2">
            {data.top_chapters.map((c) => (
              <div key={c.id} className="card flex items-center justify-between text-sm">
                <div className="min-w-0">
                  <span className="font-medium">Ch.{c.chapter_number}:</span>{" "}
                  <span className="truncate">{c.title}</span>
                </div>
                <span className="text-xs text-ink-400 shrink-0 ml-2">
                  {c.views} views · {c.word_count} words
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Series Manager
// ---------------------------------------------------------------------------

function SeriesManager({
  series,
  onRefresh,
  apiFetch,
}: {
  series: Series[];
  onRefresh: () => void;
  apiFetch: typeof window extends undefined ? any : <T>(path: string, init?: RequestInit) => Promise<T>;
}) {
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [kind, setKind] = useState("novel");
  const [status, setStatus] = useState("ongoing");
  const [published, setPublished] = useState(false);
  const [coverImage, setCoverImage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  function resetForm() {
    setTitle("");
    setDescription("");
    setKind("novel");
    setStatus("ongoing");
    setPublished(false);
    setCoverImage("");
    setEditId(null);
    setShowForm(false);
  }

  function editSeries(s: Series) {
    setEditId(s.id);
    setTitle(s.title);
    setDescription(s.description || "");
    setKind(s.kind);
    setStatus(s.status);
    setPublished(s.published);
    setCoverImage(s.cover_image || "");
    setShowForm(true);
  }

  async function handleUploadCover(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const token = localStorage.getItem("nakama_token");
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${PUBLIC_API_BASE}/creator/upload/cover`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setCoverImage(data.url);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setUploading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (editId) {
        await apiFetch(`/creator/series/${editId}`, {
          method: "PUT",
          body: JSON.stringify({
            title,
            description: description || null,
            kind,
            status,
            published,
            cover_image: coverImage || null,
          }),
        });
      } else {
        await apiFetch("/creator/series", {
          method: "POST",
          body: JSON.stringify({
            title,
            description: description || null,
            kind,
            cover_image: coverImage || null,
          }),
        });
      }
      resetForm();
      onRefresh();
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function deleteSeries(id: number) {
    if (!confirm("Delete this series and all its chapters? This cannot be undone.")) return;
    try {
      await apiFetch(`/creator/series/${id}`, { method: "DELETE" });
      onRefresh();
    } catch (e: any) {
      setError(e.message || String(e));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">My Series ({series.length})</h2>
        <button
          onClick={() => { resetForm(); setShowForm(!showForm); }}
          className="rounded-md bg-sakura-600 px-3 py-1.5 text-sm text-white hover:bg-sakura-500"
        >
          {showForm ? "Cancel" : "+ New Series"}
        </button>
      </div>

      {error && <div className="text-sm text-sakura-300">{error}</div>}

      {showForm && (
        <form onSubmit={handleSubmit} className="card space-y-4">
          <h3 className="font-semibold">{editId ? "Edit Series" : "New Series"}</h3>

          <label className="block">
            <span className="text-sm text-ink-300">Title *</span>
            <input
              type="text" value={title} onChange={(e) => setTitle(e.target.value)}
              required maxLength={255}
              className="mt-1 w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-600 focus:border-sakura-500 focus:outline-none"
            />
          </label>

          <label className="block">
            <span className="text-sm text-ink-300">Description</span>
            <textarea
              value={description} onChange={(e) => setDescription(e.target.value)}
              maxLength={5000} rows={2}
              className="mt-1 w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-600 focus:border-sakura-500 focus:outline-none"
            />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm text-ink-300">Kind</span>
              <select
                value={kind} onChange={(e) => setKind(e.target.value)}
                className="mt-1 w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 focus:border-sakura-500 focus:outline-none"
              >
                <option value="novel">Novel</option>
                <option value="comic">Comic</option>
                <option value="art">Art</option>
              </select>
            </label>

            <label className="block">
              <span className="text-sm text-ink-300">Status</span>
              <select
                value={status} onChange={(e) => setStatus(e.target.value)}
                className="mt-1 w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 focus:border-sakura-500 focus:outline-none"
              >
                <option value="ongoing">Ongoing</option>
                <option value="completed">Completed</option>
                <option value="hiatus">Hiatus</option>
              </select>
            </label>
          </div>

          <label className="block">
            <span className="text-sm text-ink-300">Cover Image</span>
            <div className="mt-1 flex items-center gap-3">
              <input
                type="text" value={coverImage}
                onChange={(e) => setCoverImage(e.target.value)}
                placeholder="URL or upload below"
                className="flex-1 rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-600 focus:border-sakura-500 focus:outline-none"
              />
              <label className="cursor-pointer rounded-md bg-ink-800 px-3 py-2 text-sm text-ink-300 hover:bg-ink-700">
                {uploading ? "Uploading..." : "Upload"}
                <input type="file" accept="image/*" onChange={handleUploadCover} className="hidden" />
              </label>
            </div>
            {coverImage && (
              <img src={coverImage} alt="Preview" className="mt-2 h-20 rounded object-cover" />
            )}
          </label>

          <label className="flex items-center gap-2 text-sm text-ink-300">
            <input
              type="checkbox" checked={published} onChange={(e) => setPublished(e.target.checked)}
              className="rounded border-ink-700 bg-ink-900"
            />
            Published (visible to readers)
          </label>

          <button
            type="submit" disabled={submitting || !title}
            className="rounded-md bg-sakura-600 px-4 py-2 text-sm font-medium text-white hover:bg-sakura-500 disabled:opacity-50"
          >
            {submitting ? "Saving..." : editId ? "Update Series" : "Create Series"}
          </button>
        </form>
      )}

      {/* Series list */}
      {series.length === 0 ? (
        <p className="text-sm text-ink-400">No series yet. Create your first one!</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {series.map((s) => (
            <div key={s.id} className="card flex flex-col">
              <div className="flex items-start gap-3">
                {s.cover_image ? (
                  <img src={s.cover_image} alt="" className="h-16 w-12 rounded object-cover shrink-0" />
                ) : (
                  <div className="h-16 w-12 rounded bg-ink-700 flex items-center justify-center text-xs text-ink-500 shrink-0">
                    {s.kind}
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-semibold truncate">{s.title}</h3>
                  <p className="text-xs text-ink-400">
                    {s.kind} · {s.status} · {s.chapter_count} ch
                  </p>
                  <div className="mt-1 flex items-center gap-1">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                      s.published ? "bg-emerald-500/20 text-emerald-300" : "bg-amber-500/20 text-amber-300"
                    }`}>
                      {s.published ? "live" : "draft"}
                    </span>
                    <span className="text-[10px] text-ink-500">{formatNumber(s.total_views)} views</span>
                  </div>
                </div>
              </div>
              <div className="mt-3 flex gap-2 border-t border-ink-700/50 pt-2">
                <button onClick={() => editSeries(s)}
                  className="text-xs text-sakura-400 hover:underline">
                  Edit
                </button>
                <button onClick={() => deleteSeries(s.id)}
                  className="text-xs text-rose-400 hover:underline">
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chapter Editor
// ---------------------------------------------------------------------------

function ChapterEditor({
  series,
  apiFetch,
  onRefresh,
}: {
  series: Series[];
  apiFetch: <T>(path: string, init?: RequestInit) => Promise<T>;
  onRefresh: () => void;
}) {
  const [selectedSeriesId, setSelectedSeriesId] = useState<number | "">("");
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [editChapter, setEditChapter] = useState<Chapter | null>(null);
  const [title, setTitle] = useState("");
  const [chapterNumber, setChapterNumber] = useState(1);
  const [content, setContent] = useState("");
  const [published, setPublished] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingChapters, setLoadingChapters] = useState(false);

  async function loadChapters(seriesId: number) {
    setLoadingChapters(true);
    setError(null);
    try {
      // Fetch series detail which includes chapters
      const s = await apiFetch<any>(`/creator/series/${seriesId}`);
      // Also fetch chapters separately
      const chs = await apiFetch<any>(`/creator/browse/${s.creator_id}/series/${seriesId}`);
      setChapters(chs.chapters || []);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setLoadingChapters(false);
    }
  }

  function handleSelectSeries(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = Number(e.target.value) || "";
    setSelectedSeriesId(id);
    setEditChapter(null);
    resetChapterForm();
    if (id) loadChapters(id);
  }

  function resetChapterForm() {
    setTitle("");
    setChapterNumber((chapters.length || 0) + 1);
    setContent("");
    setPublished(false);
  }

  function startEditChapter(c: Chapter) {
    setEditChapter(c);
    setTitle(c.title);
    setChapterNumber(c.chapter_number);
    setContent(c.content);
    setPublished(c.published);
  }

  async function handleSubmitChapter(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedSeriesId) return;
    setSubmitting(true);
    setError(null);
    try {
      if (editChapter) {
        await apiFetch(`/creator/chapters/${editChapter.id}`, {
          method: "PUT",
          body: JSON.stringify({
            title,
            chapter_number: chapterNumber,
            content,
            published,
          }),
        });
      } else {
        await apiFetch("/creator/chapters", {
          method: "POST",
          body: JSON.stringify({
            series_id: selectedSeriesId,
            title,
            chapter_number: chapterNumber,
            content,
            content_format: "markdown",
            published,
          }),
        });
      }
      setEditChapter(null);
      resetChapterForm();
      loadChapters(selectedSeriesId as number);
      onRefresh();
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function deleteChapter(id: number) {
    if (!confirm("Delete this chapter?")) return;
    try {
      await apiFetch(`/creator/chapters/${id}`, { method: "DELETE" });
      if (selectedSeriesId) loadChapters(selectedSeriesId as number);
      onRefresh();
    } catch (e: any) {
      setError(e.message || String(e));
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Chapter Editor</h2>

      {error && <div className="text-sm text-sakura-300">{error}</div>}

      {/* Series selector */}
      <label className="block">
        <span className="text-sm text-ink-300">Select Series</span>
        <select
          value={selectedSeriesId}
          onChange={handleSelectSeries}
          className="mt-1 w-full max-w-xs rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 focus:border-sakura-500 focus:outline-none"
        >
          <option value="">-- Choose a series --</option>
          {series.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title} ({s.kind})
            </option>
          ))}
        </select>
      </label>

      {/* Chapters list */}
      {selectedSeriesId && (
        <>
          {loadingChapters ? (
            <div className="text-sm text-ink-400">Loading chapters...</div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">
                  Chapters ({chapters.length})
                </h3>
                <button
                  onClick={() => { setEditChapter(null); resetChapterForm(); }}
                  className="rounded-md bg-sakura-600 px-3 py-1 text-xs text-white hover:bg-sakura-500"
                >
                  + New Chapter
                </button>
              </div>

              {chapters.length > 0 && (
                <div className="space-y-1 max-h-64 overflow-y-auto">
                  {chapters.map((c) => (
                    <div key={c.id} className="card flex items-center justify-between text-sm py-2">
                      <div className="min-w-0">
                        <span className="text-ink-400">Ch.{c.chapter_number}:</span>{" "}
                        <span className="font-medium">{c.title}</span>
                        <span className={`ml-2 text-[10px] px-1 rounded ${
                          c.published ? "bg-emerald-500/20 text-emerald-300" : "bg-ink-700 text-ink-400"
                        }`}>
                          {c.published ? "pub" : "draft"}
                        </span>
                      </div>
                      <div className="flex gap-2 shrink-0">
                        <button onClick={() => startEditChapter(c)}
                          className="text-xs text-sakura-400 hover:underline">
                          Edit
                        </button>
                        <button onClick={() => deleteChapter(c.id)}
                          className="text-xs text-rose-400 hover:underline">
                          Del
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Chapter form */}
              <form onSubmit={handleSubmitChapter} className="card space-y-4">
                <h3 className="font-semibold text-sm">
                  {editChapter ? `Edit Chapter ${editChapter.chapter_number}` : "New Chapter"}
                </h3>

                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block">
                    <span className="text-xs text-ink-300">Title *</span>
                    <input
                      type="text" value={title} onChange={(e) => setTitle(e.target.value)}
                      required maxLength={255}
                      className="mt-1 w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 focus:border-sakura-500 focus:outline-none"
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs text-ink-300">Chapter Number *</span>
                    <input
                      type="number" value={chapterNumber} onChange={(e) => setChapterNumber(Number(e.target.value))}
                      required min={1}
                      className="mt-1 w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 focus:border-sakura-500 focus:outline-none"
                    />
                  </label>
                </div>

                <label className="block">
                  <span className="text-xs text-ink-300">
                    Content * (Markdown)
                  </span>
                  <textarea
                    value={content} onChange={(e) => setContent(e.target.value)}
                    required rows={12}
                    className="mt-1 w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 font-mono placeholder:text-ink-600 focus:border-sakura-500 focus:outline-none"
                    placeholder="Write your chapter content in markdown..."
                  />
                  <span className="text-[10px] text-ink-500">
                    {content.length} chars · ~{content ? content.split(/\s+/).length : 0} words
                  </span>
                </label>

                <label className="flex items-center gap-2 text-sm text-ink-300">
                  <input
                    type="checkbox" checked={published}
                    onChange={(e) => setPublished(e.target.checked)}
                    className="rounded border-ink-700 bg-ink-900"
                  />
                  Published
                </label>

                <div className="flex gap-2">
                  <button
                    type="submit" disabled={submitting || !title || !content}
                    className="rounded-md bg-sakura-600 px-4 py-2 text-sm font-medium text-white hover:bg-sakura-500 disabled:opacity-50"
                  >
                    {submitting ? "Saving..." : editChapter ? "Update Chapter" : "Create Chapter"}
                  </button>
                  {editChapter && (
                    <button
                      type="button" onClick={() => { setEditChapter(null); resetChapterForm(); }}
                      className="rounded-md bg-ink-800 px-4 py-2 text-sm text-ink-300 hover:bg-ink-700"
                    >
                      Cancel Edit
                    </button>
                  )}
                </div>
              </form>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

function MiniMetric({
  label,
  value,
  sub,
  alert,
}: {
  label: string;
  value: string;
  sub?: string;
  alert?: boolean;
}) {
  return (
    <div className={`card ${alert ? "border-amber-500/40 bg-amber-500/5" : ""}`}>
      <p className="text-xs uppercase tracking-wide text-ink-400">{label}</p>
      <p
        className={`mt-1 text-xl font-bold tabular-nums ${
          alert ? "text-amber-300" : "text-ink-50"
        } sm:text-2xl`}
      >
        {value}
      </p>
      {sub ? <p className="mt-0.5 text-xs text-ink-400">{sub}</p> : null}
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
