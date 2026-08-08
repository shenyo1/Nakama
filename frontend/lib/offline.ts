/**
 * Offline chapter store — IndexedDB-backed reading cache.
 *
 * Pattern ported from Sanka's `offline.ts` (Lovable) and adapted for Nakama's
 * Next.js frontend + `/image?url=` proxy.
 *
 * Two stores:
 *   - `chapters` : chapter metadata (keyPath `chapterId`) -> { chapterId, title,
 *                  mangaSlug, source, savedAt, pageCount }
 *   - `pages`    : raw Blob per page (key `chapterId::pageIndex`)
 *
 * The Blobs are fetched through the same image proxy the live reader uses, so
 * offline reads are visually identical. `URL.createObjectURL` rehydrates them.
 */

import { imageProxyUrl } from "./api";

export interface OfflineChapterMeta {
  chapterId: string;
  title?: string;
  mangaSlug?: string;
  source?: string;
  savedAt: number;
  pageCount: number;
}

const DB_NAME = "nakama-offline";
const DB_VERSION = 1;
const STORE_META = "chapters";
const STORE_PAGES = "pages";

let _dbPromise: Promise<IDBDatabase> | null = null;

function openDB(): Promise<IDBDatabase> {
  if (_dbPromise) return _dbPromise;
  if (typeof indexedDB === "undefined") {
    return Promise.reject(new Error("indexedDB unavailable"));
  }
  _dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_META)) {
        db.createObjectStore(STORE_META, { keyPath: "chapterId" });
      }
      if (!db.objectStoreNames.contains(STORE_PAGES)) {
        // key = `${chapterId}::${pageIndex}`
        db.createObjectStore(STORE_PAGES);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return _dbPromise;
}

function _promisify<T>(
  req: IDBRequest<T>,
): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function _tx<T>(
  mode: IDBTransactionMode,
  fn: (stores: { meta: IDBObjectStore; pages: IDBObjectStore }) => IDBRequest<T>,
): Promise<T> {
  return openDB().then((db) => {
    const tx = db.transaction([STORE_META, STORE_PAGES], mode);
    return _promisify(fn({ meta: tx.objectStore(STORE_META), pages: tx.objectStore(STORE_PAGES) }));
  });
}

/** Resolve a ChapterImage to a proxy-backed URL (mirrors reader getSrc). */
export function proxyImageUrl(raw: string): string {
  return imageProxyUrl(raw);
}

/** True if a given chapter has any locally cached pages. */
export async function isChapterOffline(chapterId: string): Promise<boolean> {
  try {
    const meta = await _tx("readonly", ({ meta }) => meta.get(chapterId));
    return Boolean(meta) && Number((meta as OfflineChapterMeta | undefined)?.pageCount ?? 0) > 0;
  } catch {
    return false;
  }
}

/** List every chapter saved offline, newest first. */
export async function listOfflineChapters(): Promise<OfflineChapterMeta[]> {
  try {
    const all = await _tx("readonly", ({ meta }) => meta.getAll());
    return (all as OfflineChapterMeta[]).sort((a, b) => b.savedAt - a.savedAt);
  } catch {
    return [];
  }
}

/**
 * Download a whole chapter into the offline store.
 *
 * @param chapterId   stable id (e.g. `${source}/${mangaSlug}/${chapterSlug}`)
 * @param pages       array of raw image URLs (NOT yet proxy-wrapped)
 * @param meta        optional metadata (title, source, mangaSlug)
 * @param onProgress  optional `(done, total)` callback
 */
export async function downloadChapter(
  chapterId: string,
  pages: string[],
  meta: Partial<OfflineChapterMeta> = {},
  onProgress?: (done: number, total: number) => void,
): Promise<OfflineChapterMeta> {
  const total = pages.length;
  if (total === 0) throw new Error("no pages to download");

  for (let i = 0; i < total; i++) {
    const url = proxyImageUrl(pages[i]);
    const resp = await fetch(url, { credentials: "include" });
    if (!resp.ok) throw new Error(`page ${i + 1} failed (${resp.status})`);
    // Store the original URL so we can proxy it later too.
    const blob = await resp.blob();
    // eslint-disable-next-line no-await-in-loop
    await _tx("readwrite", ({ pages: s }) => s.put(blob, `${chapterId}::${i}`));
    onProgress?.(i + 1, total);
  }

  const savedMeta: OfflineChapterMeta = {
    chapterId,
    title: meta.title,
    mangaSlug: meta.mangaSlug,
    source: meta.source,
    savedAt: Date.now(),
    pageCount: total,
  };
  await _tx("readwrite", ({ meta: s }) => s.put(savedMeta));
  return savedMeta;
}

/** Rehydrate all pages of an offline chapter as object URLs. */
export async function getOfflinePages(chapterId: string): Promise<string[]> {
  const meta = await _tx("readonly", ({ meta }) => meta.get(chapterId)) as
    | OfflineChapterMeta
    | undefined;
  if (!meta || meta.pageCount === 0) return [];
  const urls: string[] = [];
  const store = (await openDB()).transaction(STORE_PAGES, "readonly").objectStore(STORE_PAGES);
  for (let i = 0; i < meta.pageCount; i++) {
    const blob = await _promisify(store.get(`${chapterId}::${i}`) as IDBRequest<Blob>);
    if (blob) urls.push(URL.createObjectURL(blob));
  }
  return urls;
}

/** Remove an offline chapter (pages + metadata). */
export async function removeOfflineChapter(chapterId: string): Promise<void> {
  const db = await openDB();
  const tx = db.transaction([STORE_META, STORE_PAGES], "readwrite");
  const meta = await _promisify(tx.objectStore(STORE_META).get(chapterId) as IDBRequest<OfflineChapterMeta | undefined>);
  tx.objectStore(STORE_META).delete(chapterId);
  if (meta) {
    for (let i = 0; i < meta.pageCount; i++) {
      tx.objectStore(STORE_PAGES).delete(`${chapterId}::${i}`);
    }
  }
  await new Promise<void>((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

/** Get total storage estimate for all offline chapters (bytes). */
export async function offlineStorageUsage(): Promise<number> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_PAGES, "readonly");
    const all = await _promisify(tx.objectStore(STORE_PAGES).getAll() as IDBRequest<Blob[]>);
    return (all as Blob[]).reduce((sum, b) => sum + (b.size || 0), 0);
  } catch {
    return 0;
  }
}
