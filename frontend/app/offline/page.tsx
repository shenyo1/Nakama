"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  listOfflineChapters,
  removeOfflineChapter,
  offlineStorageUsage,
  type OfflineChapterMeta,
} from "@/lib/offline";

export const runtime = "edge";

function formatBytes(n: number): string {
  if (n >= 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  if (n >= 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${n} B`;
}

export default function OfflinePage() {
  const [chapters, setChapters] = useState<OfflineChapterMeta[]>([]);
  const [usage, setUsage] = useState(0);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [chs, bytes] = await Promise.all([listOfflineChapters(), offlineStorageUsage()]);
      setChapters(chs);
      setUsage(bytes);
    } catch {
      // IndexedDB unavailable
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleDelete = useCallback(
    async (id: string) => {
      await removeOfflineChapter(id);
      refresh();
    },
    [refresh],
  );

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">📥 Offline Library</h1>
          <p className="text-sm text-ink-400">
            Chapter yang tersimpan untuk dibaca tanpa internet ·{" "}
            <span className="tabular-nums">{formatBytes(usage)}</span>
          </p>
        </div>
        <Link href="/" className="btn text-xs">
          ← Home
        </Link>
      </div>

      {loading ? (
        <p className="py-10 text-center text-ink-400">Memuat…</p>
      ) : chapters.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-ink-700 py-16 text-center">
          <div className="text-5xl">🗂️</div>
          <p className="text-ink-300">Belum ada chapter yang disimpan offline.</p>
          <p className="max-w-sm text-xs text-ink-500">
            Buka chapter manga/manhwa/manhua dan tekan tombol <b>⬇️ Offline</b> di
            reader untuk menyimpannya di sini.
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {chapters.map((c) => (
            <li
              key={c.chapterId}
              className="flex items-center justify-between rounded-xl border border-ink-800 bg-ink-900/40 px-4 py-3"
            >
              <div className="min-w-0">
                <p className="truncate font-medium">
                  {c.title || c.chapterId}
                </p>
                <p className="text-xs text-ink-400">
                  {c.source && <span className="text-sakura-400">{c.source}</span>}{" "}
                  · {c.pageCount} halaman ·{" "}
                  {new Date(c.savedAt).toLocaleDateString()}
                </p>
              </div>
              <div className="ml-3 flex shrink-0 items-center gap-2">
                <button
                  onClick={() => handleDelete(c.chapterId)}
                  className="rounded px-2 py-1 text-xs text-red-400 hover:bg-ink-800/50"
                >
                  Hapus
                </button>
                {c.source && c.mangaSlug && (
                  <Link
                    href={`/comic/${c.source}/chapter/${c.chapterId}`}
                    className="btn px-3 text-xs"
                  >
                    Baca
                  </Link>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
