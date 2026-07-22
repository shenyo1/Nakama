"use client";

import { useState, useEffect } from "react";

export function SearchBox({
  kind,
  source,
  placeholder = "Search...",
}: {
  kind: string;
  source: string;
  placeholder?: string;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      setShow(false);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `/api/backend/${kind}/${source}/search/${encodeURIComponent(query)}`
        );
        if (res.ok) {
          const body = await res.json();
          const data = body.data;
          setResults(Array.isArray(data) ? data.slice(0, 6) : []);
          setShow(true);
        }
      } catch {
        // silent
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query, kind, source]);

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setShow(true)}
        onBlur={() => setTimeout(() => setShow(false), 200)}
        placeholder={placeholder}
        className="input"
      />
      {loading ? (
        <div className="absolute right-3 top-2.5 text-xs text-ink-400">...</div>
      ) : null}
      {show && results.length > 0 ? (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-ink-700 bg-ink-900 shadow-xl max-h-64 overflow-y-auto">
          {results.map((item, i) => {
            const r = item as Record<string, unknown>;
            return (
              <a
                key={i}
                href={
                  kind === "comic"
                    ? `/${kind}/${source}/manga/${r.slug || ""}`
                    : kind === "anime"
                      ? `/${kind}/${source}/detail/${r.slug || ""}`
                      : `/${kind}/${source}/detail/${r.slug || ""}`
                }
                className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-ink-800"
              >
                {typeof r.thumbnail === "string" ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={`/api/backend/image?url=${encodeURIComponent(r.thumbnail)}`} alt="" className="h-10 w-8 rounded object-cover shrink-0" />
                ) : null}
                <span className="truncate text-ink-200">{String(r.title || r.slug || "")}</span>
              </a>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
