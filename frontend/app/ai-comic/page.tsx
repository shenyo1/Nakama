"use client";

import { useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PanelImage {
  panel: number;
  image_url: string;
}

interface ComicResult {
  public_id: string;
  prompt: string;
  style: string;
  panel_count: number;
  panel_descriptions: string[];
  images: PanelImage[];
}

interface GalleryItem {
  public_id: string;
  prompt: string;
  style: string;
  panel_count: number;
  images: PanelImage[];
  created_at: string;
}

const STYLES = [
  { value: "manga", label: "Manga", emoji: "🇯🇵" },
  { value: "manhwa", label: "Manhwa", emoji: "🇰🇷" },
  { value: "western", label: "Western", emoji: "🇺🇸" },
  { value: "webtoon", label: "Webtoon", emoji: "🌐" },
] as const;

const PANEL_OPTIONS = [1, 2, 3, 4, 5, 6] as const;

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api/backend";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AiComicPage() {
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState<string>("manga");
  const [panels, setPanels] = useState(4);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ComicResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [gallery, setGallery] = useState<GalleryItem[]>([]);
  const [galleryLoading, setGalleryLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"generate" | "gallery">("generate");

  // Load gallery on mount
  useEffect(() => {
    loadGallery();
  }, []);

  async function loadGallery() {
    setGalleryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ai/gallery?limit=20`);
      const json = await res.json();
      if (json.ok && json.data?.items) {
        setGallery(json.data.items);
      }
    } catch {
      // Gallery is best-effort
    } finally {
      setGalleryLoading(false);
    }
  }

  async function handleGenerate() {
    if (!prompt.trim() || prompt.trim().length < 5) {
      setError("Please enter at least 5 characters for your comic prompt.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API_BASE}/ai/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt.trim(),
          style,
          panels,
        }),
      });

      const json = await res.json();

      if (!json.ok) {
        setError(json.error || json.detail || "Generation failed");
        return;
      }

      setResult(json.data as ComicResult);
      // Reload gallery to include the new comic
      loadGallery();
    } catch (e: any) {
      setError(e.message || "Network error. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  // -----------------------------------------------------------------------
  // Render helpers
  // -----------------------------------------------------------------------

  const styleLabel = STYLES.find((s) => s.value === style);

  return (
    <div className="container-page py-6 sm:py-10">
      {/* Header */}
      <div className="mb-8 text-center">
        <h1 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
          <span className="text-sakura-400">AI</span>{" "}
          <span className="text-ink-50">Comic Generator</span>
        </h1>
        <p className="mt-2 text-sm text-ink-400">
          Describe a scene or story and let AI generate comic panels for you
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex justify-center gap-1 rounded-lg bg-ink-800/50 p-1 max-w-xs mx-auto">
        <button
          onClick={() => setActiveTab("generate")}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition ${
            activeTab === "generate"
              ? "bg-sakura-500 text-white"
              : "text-ink-300 hover:text-white"
          }`}
        >
          Generate
        </button>
        <button
          onClick={() => setActiveTab("gallery")}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition ${
            activeTab === "gallery"
              ? "bg-sakura-500 text-white"
              : "text-ink-300 hover:text-white"
          }`}
        >
          Gallery
        </button>
      </div>

      {/* Generate Tab */}
      {activeTab === "generate" && (
        <div className="mx-auto max-w-2xl space-y-6">
          {/* Prompt input */}
          <div>
            <label
              htmlFor="comic-prompt"
              className="mb-2 block text-sm font-medium text-ink-200"
            >
              Your comic story or scene
            </label>
            <textarea
              id="comic-prompt"
              rows={4}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. A samurai cat walking through a neon-lit Tokyo street at night, rain falling gently..."
              className="w-full rounded-lg border border-ink-700 bg-ink-900 px-4 py-3 text-sm text-ink-100 placeholder-ink-600 focus:border-sakura-500 focus:outline-none focus:ring-1 focus:ring-sakura-500 resize-none"
              disabled={loading}
            />
            <p className="mt-1 text-xs text-ink-500">
              Tip: Number your panels like &quot;1. First scene 2. Second
              scene&quot; for precise control
            </p>
          </div>

          {/* Style + Panels row */}
          <div className="grid grid-cols-2 gap-4">
            {/* Style selector */}
            <div>
              <label className="mb-2 block text-sm font-medium text-ink-200">
                Art Style
              </label>
              <div className="grid grid-cols-2 gap-2">
                {STYLES.map((s) => (
                  <button
                    key={s.value}
                    onClick={() => setStyle(s.value)}
                    disabled={loading}
                    className={`rounded-lg border px-3 py-2.5 text-sm font-medium transition ${
                      style === s.value
                        ? "border-sakura-500 bg-sakura-500/10 text-sakura-300"
                        : "border-ink-700 bg-ink-900 text-ink-400 hover:border-ink-600 hover:text-ink-200"
                    } disabled:opacity-50`}
                  >
                    {s.emoji} {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Panel count */}
            <div>
              <label className="mb-2 block text-sm font-medium text-ink-200">
                Panels
              </label>
              <div className="grid grid-cols-3 gap-2">
                {PANEL_OPTIONS.map((n) => (
                  <button
                    key={n}
                    onClick={() => setPanels(n)}
                    disabled={loading}
                    className={`rounded-lg border px-3 py-2.5 text-sm font-medium transition ${
                      panels === n
                        ? "border-sakura-500 bg-sakura-500/10 text-sakura-300"
                        : "border-ink-700 bg-ink-900 text-ink-400 hover:border-ink-600 hover:text-ink-200"
                    } disabled:opacity-50`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={loading || !prompt.trim()}
            className="w-full rounded-lg bg-sakura-500 py-3 text-sm font-semibold text-white transition hover:bg-sakura-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <svg
                  className="h-4 w-4 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Generating panels...
              </span>
            ) : (
              `Generate ${panels}-Panel ${styleLabel?.label || "Comic"}`
            )}
          </button>

          {/* Error */}
          {error && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
              {error}
            </div>
          )}

          {/* Result */}
          {result && (
            <div className="space-y-4 rounded-xl border border-ink-700 bg-ink-900/50 p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-ink-200">
                  Generated Comic{" "}
                  <span className="ml-2 rounded bg-ink-800 px-2 py-0.5 text-xs text-ink-400">
                    {result.style} · {result.panel_count} panels
                  </span>
                </h3>
                <span className="text-xs text-ink-500">
                  ID: {result.public_id}
                </span>
              </div>

              {/* Panel grid */}
              <div
                className={`grid gap-3 ${
                  result.panel_count <= 2
                    ? "grid-cols-1 sm:grid-cols-2"
                    : result.panel_count <= 4
                      ? "grid-cols-2"
                      : "grid-cols-2 lg:grid-cols-3"
                }`}
              >
                {result.images.map((img, i) => (
                  <div
                    key={img.panel}
                    className="overflow-hidden rounded-lg border border-ink-700 bg-ink-950"
                  >
                    {/* Placeholder panel — real images come from image_generate */}
                    <div className="relative aspect-[4/3] bg-ink-900 flex items-center justify-center">
                      <div className="text-center">
                        <div className="mb-2 text-4xl">
                          {style === "manga"
                            ? "🇯🇵"
                            : style === "manhwa"
                              ? "🇰🇷"
                              : style === "western"
                                ? "🇺🇸"
                                : "🌐"}
                        </div>
                        <p className="text-xs font-medium text-ink-400">
                          Panel {img.panel}
                        </p>
                        <p className="mt-1 px-4 text-xs leading-relaxed text-ink-600 line-clamp-3">
                          {result.panel_descriptions[i] || "Scene description"}
                        </p>
                      </div>
                    </div>
                    <div className="border-t border-ink-700 px-3 py-2">
                      <p className="text-xs text-ink-400">
                        Panel {img.panel} of {result.panel_count}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Prompt display */}
              <details className="group">
                <summary className="cursor-pointer text-xs font-medium text-ink-500 hover:text-ink-300">
                  Show original prompt
                </summary>
                <p className="mt-2 text-xs leading-relaxed text-ink-400">
                  {result.prompt}
                </p>
              </details>
            </div>
          )}
        </div>
      )}

      {/* Gallery Tab */}
      {activeTab === "gallery" && (
        <div className="mx-auto max-w-5xl">
          {galleryLoading ? (
            <div className="flex justify-center py-12">
              <svg
                className="h-6 w-6 animate-spin text-ink-500"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            </div>
          ) : gallery.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-4xl">🎨</p>
              <p className="mt-3 text-sm text-ink-400">
                No comics generated yet. Be the first!
              </p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {gallery.map((item) => (
                <div
                  key={item.public_id}
                  className="overflow-hidden rounded-xl border border-ink-700 bg-ink-900/50 transition hover:border-ink-600"
                >
                  {/* Thumbnail grid */}
                  <div className="grid grid-cols-2 gap-0.5 bg-ink-950 p-3">
                    {item.images.slice(0, 4).map((img) => (
                      <div
                        key={img.panel}
                        className="relative aspect-square overflow-hidden rounded bg-ink-900"
                      >
                        <div className="flex h-full w-full items-center justify-center text-2xl">
                          {item.style === "manga"
                            ? "🇯🇵"
                            : item.style === "manhwa"
                              ? "🇰🇷"
                              : item.style === "western"
                                ? "🇺🇸"
                                : "🌐"}
                        </div>
                      </div>
                    ))}
                    {item.panel_count > 4 && (
                      <div className="flex aspect-square items-center justify-center rounded bg-ink-900 text-xs text-ink-600">
                        +{item.panel_count - 4}
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="px-3 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-ink-800 px-2 py-0.5 text-xs font-medium text-ink-300">
                        {item.style}
                      </span>
                      <span className="text-xs text-ink-500">
                        {item.panel_count} panels
                      </span>
                    </div>
                    <p className="mt-1.5 text-xs leading-relaxed text-ink-400 line-clamp-2">
                      {item.prompt}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
