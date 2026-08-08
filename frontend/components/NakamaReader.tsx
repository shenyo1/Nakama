"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  downloadChapter,
  isChapterOffline,
  getOfflinePages,
  removeOfflineChapter,
} from "@/lib/offline";
import { usePinchZoom } from "@/lib/usePinchZoom";

interface ChapterImage {
  url?: string;
  src?: string;
  [k: string]: unknown;
}

interface ChapterData {
  title?: string;
  slug?: string;
  images?: ChapterImage[];
  chapter?: number | string;
  prev_chapter?: string;
  next_chapter?: string;
  [k: string]: unknown;
}

/** Reading modes */
type ReaderMode = "scroll" | "single" | "double";
type ReadingDirection = "ltr" | "rtl";

/** Persisted preferences */
interface ReaderPrefs {
  mode: ReaderMode;
  direction: ReadingDirection;
  darkMode: boolean;
  fitToWidth: boolean;
}

const PREFS_KEY = "nakama_reader_prefs";

function loadPrefs(): ReaderPrefs {
  if (typeof window === "undefined") return { mode: "scroll", direction: "ltr", darkMode: true, fitToWidth: true };
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { mode: "scroll", direction: "ltr", darkMode: true, fitToWidth: true };
}

function savePrefs(prefs: ReaderPrefs) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch {}
}

export default function NakamaReader({
  chapter,
  source,
  mangaSlug,
}: {
  chapter: ChapterData;
  source: string;
  mangaSlug: string;
}) {
  const [prefs, setPrefs] = useState<ReaderPrefs>(loadPrefs);
  const [currentPage, setCurrentPage] = useState(0);
  const [loadedImages, setLoadedImages] = useState<Set<number>>(new Set([0, 1, 2]));
  const containerRef = useRef<HTMLDivElement>(null);
  const zoom = usePinchZoom();

  const images = chapter.images || [];
  const totalPages = images.length;

  // ── Offline state ─────────────────────────────────────
  const chapterId = `${source}/${mangaSlug}/${chapter.slug || chapter.chapter || "chapter"}`;
  const [isOffline, setIsOffline] = useState(false);
  const [offlineProgress, setOfflineProgress] = useState<number | null>(null);
  const [offlinePages, setOfflinePages] = useState<string[] | null>(null);
  const [offlineError, setOfflineError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (await isChapterOffline(chapterId)) {
          const pages = await getOfflinePages(chapterId);
          if (!cancelled && pages.length > 0) {
            setIsOffline(true);
            setOfflinePages(pages);
          }
        }
      } catch {}
    })();
    return () => {
      cancelled = true;
    };
  }, [chapterId]);

  const handleDownloadOffline = useCallback(async () => {
    const raws = images.map((img) => img.url || img.src || (typeof img === "string" ? img : "")).filter(Boolean);
    if (raws.length === 0) return;
    setOfflineError(null);
    setOfflineProgress(0);
    try {
      await downloadChapter(chapterId, raws as string[], {
        title: chapter.title || chapter.slug || "Chapter",
        source,
        mangaSlug,
      }, (done, total) => setOfflineProgress(Math.round((done / total) * 100)));
      setIsOffline(true);
      const pages = await getOfflinePages(chapterId);
      setOfflinePages(pages);
      setOfflineProgress(null);
    } catch (e) {
      setOfflineProgress(null);
      setOfflineError(`Gagal unduh: ${e instanceof Error ? e.message : "unknown"}`);
    }
  }, [images, chapterId, source, mangaSlug, chapter.title, chapter.slug]);

  const handleRemoveOffline = useCallback(async () => {
    await removeOfflineChapter(chapterId);
    setIsOffline(false);
    setOfflinePages(null);
    if (offlinePages) for (const u of offlinePages) URL.revokeObjectURL(u);
    setOfflinePages(null);
  }, [chapterId, offlinePages]);


  // ── Persist prefs ──────────────────────────────────────
  useEffect(() => {
    savePrefs(prefs);
  }, [prefs]);

  // ── Keyboard navigation ────────────────────────────────
  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        if (prefs.mode === "scroll") return; // natural scroll
        setCurrentPage((p) => Math.min(p + 1, totalPages - 1));
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        if (prefs.mode === "scroll") return;
        setCurrentPage((p) => Math.max(p - 1, 0));
      } else if (e.key === "f") {
        setPrefs((p) => ({ ...p, fitToWidth: !p.fitToWidth }));
      } else if (e.key === "m") {
        setPrefs((p) => ({
          ...p,
          mode: p.mode === "scroll" ? "single" : p.mode === "single" ? "double" : "scroll",
        }));
      } else if (e.key === "d") {
        setPrefs((p) => ({ ...p, darkMode: !p.darkMode }));
      }
    },
    [prefs.mode, totalPages]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [handleKey]);

  // ── Lazy load more images on scroll ────────────────────
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    if (scrollHeight - scrollTop - clientHeight < 2000) {
      // Load next batch
      setLoadedImages((prev) => {
        const next = new Set(prev);
        const maxLoaded = Math.max(...prev);
        for (let i = maxLoaded + 1; i < Math.min(maxLoaded + 6, totalPages); i++) {
          next.add(i);
        }
        return next;
      });
    }
  }, [totalPages]);

  // ── TTS (Text-to-Speech) ────────────────────────────────
  const speak = useCallback((text: string) => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "id-ID";
      utterance.rate = 0.9;
      window.speechSynthesis.speak(utterance);
    }
  }, []);

  // ── Get image src ──────────────────────────────────────
  const getSrc = (img: ChapterImage): string => {
    const raw = img.url || img.src || (typeof img === "string" ? img : "");
    return `/image?url=${encodeURIComponent(raw)}`;
  };

  // ── Double page pairs ──────────────────────────────────
  const doublePages: [ChapterImage, ChapterImage | null][] = [];
  if (prefs.mode === "double") {
    for (let i = 0; i < images.length; i += 2) {
      doublePages.push([images[i], images[i + 1] || null]);
    }
  }

  const bg = prefs.darkMode ? "bg-[#0a0a0f]" : "bg-[#f5f5f0]";
  const textColor = prefs.darkMode ? "text-ink-100" : "text-gray-900";
  const controlsBg = prefs.darkMode ? "bg-ink-900/80" : "bg-white/80";

  return (
    <div className={`relative min-h-screen ${bg} ${textColor}`}>
      {/* ── Top bar: controls ─────────────────────────── */}
      <div className={`sticky top-0 z-30 ${controlsBg} backdrop-blur border-b ${prefs.darkMode ? "border-ink-800" : "border-gray-200"}`}>
        <div className="mx-auto flex max-w-4xl items-center justify-between px-3 py-2 text-xs">
          <div className="flex items-center gap-2">
            {/* Mode toggle */}
            <button
              onClick={() =>
                setPrefs((p) => ({
                  ...p,
                  mode: p.mode === "scroll" ? "single" : p.mode === "single" ? "double" : "scroll",
                }))
              }
              className="rounded px-2 py-1 hover:bg-ink-800/50"
              title="Toggle mode (M)"
            >
              {prefs.mode === "scroll" ? "📜 Scroll" : prefs.mode === "double" ? "📖 Spread" : "📄 Page"}
            </button>

            {/* Fit toggle */}
            <button
              onClick={() => setPrefs((p) => ({ ...p, fitToWidth: !p.fitToWidth }))}
              className="rounded px-2 py-1 hover:bg-ink-800/50"
              title="Toggle fit (F)"
            >
              {prefs.fitToWidth ? "↔ Fit" : "↕ Full"}
            </button>

            {/* Dark mode */}
            <button
              onClick={() => setPrefs((p) => ({ ...p, darkMode: !p.darkMode }))}
              className="rounded px-2 py-1 hover:bg-ink-800/50"
              title="Toggle dark mode (D)"
            >
              {prefs.darkMode ? "☀️" : "🌙"}
            </button>

            {/* TTS */}
            <button
              onClick={() => speak(chapter.title || "Chapter")}
              className="rounded px-2 py-1 hover:bg-ink-800/50"
              title="Read aloud"
            >
              🔊
            </button>

            {/* Offline download */}
            {offlineProgress !== null ? (
              <span className="tabular-nums text-sakura-400" title="Mengunduh chapter…">
                ⬇️ {offlineProgress}%
              </span>
            ) : isOffline ? (
              <button
                onClick={handleRemoveOffline}
                className="rounded px-2 py-1 text-emerald-400 hover:bg-ink-800/50"
                title="Hapus dari offline"
              >
                📥 Saved
              </button>
            ) : (
              <button
                onClick={handleDownloadOffline}
                disabled={offlineProgress !== null}
                className="rounded px-2 py-1 hover:bg-ink-800/50 disabled:opacity-40"
                title="Simpan offline"
              >
                ⬇️ Offline
              </button>
            )}
          </div>

          {/* Page counter */}
          {prefs.mode !== "scroll" && (
            <span className="tabular-nums text-ink-400">
              {currentPage + 1} / {totalPages}
            </span>
          )}
        </div>
      </div>

      {/* ── Page/single mode ─────────────────────────── */}
      {(prefs.mode === "single" || prefs.mode === "double") && totalPages > 0 && (
        <div
          className="flex min-h-[calc(100vh-40px)] cursor-pointer items-center justify-center"
          onClick={(e) => {
            const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
            const x = e.clientX - rect.left;
            if (x < rect.width * 0.3) setCurrentPage((p) => Math.max(p - 1, 0));
            else setCurrentPage((p) => Math.min(p + 1, totalPages - 1));
          }}
        >
          {prefs.mode === "single" ? (
            <img
              src={offlinePages ? offlinePages[currentPage] : getSrc(images[currentPage])}
              alt={`Page ${currentPage + 1}`}
              className={`max-h-[calc(100vh-60px)] select-none ${prefs.fitToWidth ? "w-full max-w-4xl" : "h-full"}`}
              draggable={false}
              style={zoom.bind.style}
            />
          ) : (
            <div className="flex gap-0">
              {doublePages[currentPage]?.map((img, i) =>
                img ? (
                  <img
                    key={i}
                    src={getSrc(img)}
                    alt={`Page ${currentPage * 2 + i + 1}`}
                    className={`max-h-[calc(100vh-60px)] select-none ${prefs.fitToWidth ? "w-1/2 max-w-2xl" : "h-full"}`}
                    draggable={false}
                  />
                ) : null
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Scroll mode ──────────────────────────────── */}
      {prefs.mode === "scroll" && (
        <div ref={containerRef} onScroll={handleScroll} className="mx-auto max-w-4xl space-y-0">
          {images.map((img, i) => {
            if (!loadedImages.has(i)) {
              return (
                <div key={i} className="flex h-96 items-center justify-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-sakura-400 border-t-transparent" />
                </div>
              );
            }
            return (
              <img
                key={i}
                src={getSrc(img)}
                alt={`Page ${i + 1}`}
                className={`mx-auto select-none ${prefs.fitToWidth ? "w-full" : "h-auto"}`}
                loading="lazy"
                draggable={false}
              />
            );
          })}
        </div>
      )}

      {/* ── Bottom: chapter navigation ────────────────── */}
      <div className={`sticky bottom-0 z-30 ${controlsBg} backdrop-blur border-t ${prefs.darkMode ? "border-ink-800" : "border-gray-200"}`}>
        <div className="mx-auto flex max-w-4xl items-center justify-between px-3 py-2 text-xs">
          {chapter.prev_chapter ? (
            <a
              href={`/comic/${source}/chapter/${chapter.prev_chapter}`}
              className="rounded px-2 py-1 text-sakura-400 hover:bg-ink-800/50"
            >
              ← Prev
            </a>
          ) : (
            <span className="text-ink-600">← Prev</span>
          )}

          <div className="flex items-center gap-1">
            {prefs.mode === "single" && (
              <>
                <button onClick={zoom.zoomOut} className="rounded px-2 py-1 hover:bg-ink-800/50" title="Perkecil (−)">
                  −
                </button>
                <span className="tabular-nums text-ink-400">{Math.round(zoom.scale * 100)}%</span>
                <button onClick={zoom.zoomIn} className="rounded px-2 py-1 hover:bg-ink-800/50" title="Perbesar (+)">
                  +
                </button>
                <button onClick={zoom.reset} className="rounded px-2 py-1 text-ink-400 hover:bg-ink-800/50" title="Reset zoom">
                  ↺
                </button>
              </>
            )}
            <a
              href={`/comic/${source}/manga/${mangaSlug}`}
              className="rounded px-2 py-1 text-ink-400 hover:bg-ink-800/50"
            >
              Chapter list
            </a>
          </div>

          {chapter.next_chapter ? (
            <a
              href={`/comic/${source}/chapter/${chapter.next_chapter}`}
              className="rounded px-2 py-1 text-sakura-400 hover:bg-ink-800/50"
            >
              Next →
            </a>
          ) : (
            <span className="text-ink-600">Next →</span>
          )}
        </div>
        {offlineError && (
          <div className="px-3 pb-1 text-center text-[10px] text-red-400">{offlineError}</div>
        )}
      </div>

      {/* ── Keyboard shortcuts help ──────────────────── */}
      <div className="fixed bottom-12 right-3 z-40 text-[10px] text-ink-600">
        M:mode · F:fit · D:dark · ←→:page
      </div>
    </div>
  );
}
