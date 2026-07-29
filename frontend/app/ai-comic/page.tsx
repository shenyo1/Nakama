"use client";

import { useState } from "react";

const STYLES = [
  { id: "manga", name: "Manga", emoji: "🇯🇵", desc: "B&W Japanese style" },
  { id: "manhwa", name: "Manhwa", emoji: "🇰🇷", desc: "Color Korean style" },
  { id: "western", name: "Western", emoji: "🇺🇸", desc: "American comic style" },
  { id: "webtoon", name: "Webtoon", emoji: "📱", desc: "Digital webtoon art" },
];

export default function AIComicPage() {
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("manga");
  const [panels, setPanels] = useState(4);
  const [characters, setCharacters] = useState("");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [gallery, setGallery] = useState<any[]>([]);
  const [showGallery, setShowGallery] = useState(false);

  const generate = async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    setError("");
    setResult(null);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE || "https://mynakama.web.id"}/ai/generate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt, style, panels, characters: characters || undefined }),
        }
      );
      const data = await res.json();
      if (data.ok) {
        setResult(data.data);
      } else {
        setError(data.error || "Generation failed");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setGenerating(false);
    }
  };

  const loadGallery = async () => {
    setShowGallery(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE || "https://mynakama.web.id"}/ai/gallery?limit=12`
      );
      const data = await res.json();
      if (data.ok) setGallery(data.data);
    } catch {}
  };

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      {/* Header */}
      <header className="space-y-2">
        <h1 className="font-display text-2xl font-bold sm:text-3xl">
          🤖 AI Comic Generator
        </h1>
        <p className="text-sm text-ink-400">
          Turn your story ideas into comic pages with AI. Describe a scene, pick a style, and let the magic happen!
        </p>
      </header>

      {/* Generator form */}
      <div className="card space-y-4">
        {/* Prompt */}
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-ink-300">
            Story / Scene Description
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., A young warrior stands at the edge of a cliff, overlooking a mystical kingdom at sunset. Cherry blossoms dance in the wind..."
            className="w-full rounded-lg border border-ink-700 bg-ink-900 px-4 py-3 text-sm text-ink-100 placeholder:text-ink-600 focus:border-sakura-500 focus:outline-none focus:ring-1 focus:ring-sakura-500"
            rows={4}
            maxLength={500}
          />
          <p className="mt-1 text-right text-xs text-ink-600">{prompt.length}/500</p>
        </div>

        {/* Style selector */}
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-ink-300">Art Style</label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {STYLES.map((s) => (
              <button
                key={s.id}
                onClick={() => setStyle(s.id)}
                className={`rounded-lg border p-3 text-left transition-colors ${
                  style === s.id
                    ? "border-sakura-500 bg-sakura-500/10 text-sakura-300"
                    : "border-ink-700 bg-ink-900 text-ink-400 hover:border-ink-600"
                }`}
              >
                <span className="text-lg">{s.emoji}</span>
                <p className="mt-1 text-sm font-medium">{s.name}</p>
                <p className="text-xs opacity-60">{s.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Panels + Characters */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-ink-300">
              Panels: {panels}
            </label>
            <input
              type="range"
              min={1}
              max={6}
              value={panels}
              onChange={(e) => setPanels(Number(e.target.value))}
              className="w-full accent-sakura-500"
            />
            <div className="mt-1 flex justify-between text-[10px] text-ink-600">
              <span>1</span>
              <span>2</span>
              <span>3</span>
              <span>4</span>
              <span>5</span>
              <span>6</span>
            </div>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-ink-300">
              Characters (optional)
            </label>
            <input
              type="text"
              value={characters}
              onChange={(e) => setCharacters(e.target.value)}
              placeholder="e.g., tall warrior with red hair, small dragon companion"
              className="w-full rounded-lg border border-ink-700 bg-ink-900 px-4 py-3 text-sm text-ink-100 placeholder:text-ink-600 focus:border-sakura-500 focus:outline-none"
              maxLength={200}
            />
          </div>
        </div>

        {/* Generate button */}
        <button
          onClick={generate}
          disabled={!prompt.trim() || generating}
          className="btn-primary w-full py-3 text-base disabled:opacity-50"
        >
          {generating ? (
            <span className="flex items-center justify-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Generating {panels} panels...
            </span>
          ) : (
            `✨ Generate ${panels} Panel Comic`
          )}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="card border-sakura-500/30 bg-sakura-500/5 text-sm text-sakura-200">
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold">Your Generated Comic</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {result.pages?.map((page: any) => (
              <div key={page.panel_number} className="card space-y-2">
                <p className="text-xs font-semibold text-ink-400">
                  Panel {page.panel_number}
                </p>
                <div className="aspect-[3/4] overflow-hidden rounded-lg bg-ink-800">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={page.image_url}
                    alt={`Panel ${page.panel_number}`}
                    className="h-full w-full object-cover"
                  />
                </div>
                <p className="text-[10px] leading-relaxed text-ink-500">
                  Prompt: {page.prompt_used.slice(0, 100)}...
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Gallery */}
      <div className="space-y-4">
        <button
          onClick={showGallery ? () => setShowGallery(false) : loadGallery}
          className="text-sm text-sakura-400 hover:underline"
        >
          {showGallery ? "Hide Gallery" : "Browse Community Gallery →"}
        </button>

        {showGallery && gallery.length > 0 && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {gallery.map((item) => (
              <div key={item.id} className="card space-y-2">
                <div className="aspect-[3/4] overflow-hidden rounded-lg bg-ink-800">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={item.thumbnail}
                    alt={item.prompt}
                    className="h-full w-full object-cover"
                  />
                </div>
                <p className="text-xs text-ink-400 truncate">{item.prompt}</p>
                <div className="flex items-center justify-between text-[10px] text-ink-500">
                  <span>{item.style}</span>
                  <span>❤️ {item.likes}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
