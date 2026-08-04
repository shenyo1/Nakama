"use client";

import { useState } from "react";

// Inline SVG icons (lightweight, no dependency)
const IconShare = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
    <polyline points="16 6 12 2 8 6" />
    <line x1="12" y1="2" x2="12" y2="15" />
  </svg>
);
const IconTwitter = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
);
const IconTelegram = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
    <path d="M22.05 1.575c-.393-.016-.873.06-1.218.21L2.733 9.252c-.86.334-1.473.83-1.473 1.568 0 .738.61 1.234 1.47 1.568l4.502 1.74 2.093 6.49c.105.325.32.56.61.56.22 0 .39-.1.55-.26l2.41-2.29 4.77 3.523c.395.275.735.4 1.03.4.38 0 .69-.18.87-.53l4.65-19.1c.16-.65-.05-1.18-.55-1.48a1.47 1.47 0 0 0-.76-.24z" />
  </svg>
);
const IconWhatsApp = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51l-.57-.01c-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z" />
  </svg>
);
const IconLink = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
  </svg>
);
const IconCheck = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <polyline points="20 6 9 17 4 12" />
  </svg>
);
const IconImage = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <circle cx="8.5" cy="8.5" r="1.5" />
    <polyline points="21 15 16 10 5 21" />
  </svg>
);

interface ShareCardProps {
  title: string;
  kind: "anime" | "comic" | "novel";
  source: string;
  slug: string;
  thumbnail?: string;
  description?: string;
  episodes?: string;
  genres?: string[];
  url: string;
}

export default function ShareCard({
  title,
  kind,
  source,
  slug,
  thumbnail,
  description,
  episodes,
  genres,
  url,
}: ShareCardProps) {
  const [copied, setCopied] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  const kindLabel = kind === "anime" ? "Anime" : kind === "comic" ? "Comic" : "Novel";

  // Share targets
  const shareTwitter = () => {
    const text = `Reading: ${title}\n\n${description ? description.slice(0, 100) + "..." : ""}\n\nRead on Nakama: ${url}`;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`, "_blank");
  };

  const shareTelegram = () => {
    const text = `${title}\n\n${description ? description.slice(0, 150) + "..." : ""}\n\n[Read on Nakama](${url})`;
    window.open(`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`, "_blank");
  };

  const shareWhatsApp = () => {
    const text = `${title}\n\n${description ? description.slice(0, 150) + "..." : ""}\n\n${url}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank");
  };

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const shareNative = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `${title}`,
          text: description?.slice(0, 150),
          url,
        });
      } catch {}
    } else {
      copyLink();
    }
  };

  return (
    <div className="space-y-2">
      {/* Share buttons row */}
      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={shareNative}
          className="flex items-center gap-1.5 rounded-full bg-sakura-500/20 px-3 py-1.5 text-xs font-medium text-sakura-400 hover:bg-sakura-500/30 transition-colors"
        >
          <IconShare /> Share
        </button>
        <button
          onClick={shareTwitter}
          className="flex items-center gap-1.5 rounded-full bg-ink-800 px-3 py-1.5 text-xs font-medium text-ink-200 hover:bg-ink-700 transition-colors"
        >
          <IconTwitter /> Tweet
        </button>
        <button
          onClick={shareTelegram}
          className="flex items-center gap-1.5 rounded-full bg-ink-800 px-3 py-1.5 text-xs font-medium text-ink-200 hover:bg-ink-700 transition-colors"
        >
          <IconTelegram /> Telegram
        </button>
        <button
          onClick={shareWhatsApp}
          className="flex items-center gap-1.5 rounded-full bg-ink-800 px-3 py-1.5 text-xs font-medium text-ink-200 hover:bg-ink-700 transition-colors"
        >
          <IconWhatsApp /> WhatsApp
        </button>
        <button
          onClick={copyLink}
          className="flex items-center gap-1.5 rounded-full bg-ink-800 px-3 py-1.5 text-xs font-medium text-ink-200 hover:bg-ink-700 transition-colors"
        >
          {copied ? <><IconCheck /> Copied</> : <><IconLink /> Copy</>}
        </button>
        <button
          onClick={() => setShowPreview(!showPreview)}
          className="flex items-center gap-1.5 rounded-full bg-ink-800 px-3 py-1.5 text-xs font-medium text-ink-200 hover:bg-ink-700 transition-colors"
        >
          <IconImage /> Preview
        </button>
      </div>

      {/* Preview card */}
      {showPreview && (
        <div className="overflow-hidden rounded-xl border border-ink-700 bg-gradient-to-br from-ink-900 to-ink-950 p-4">
          <div className="flex gap-3">
            {thumbnail && (
              <div className="h-20 w-16 flex-shrink-0 overflow-hidden rounded-lg">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={thumbnail} alt={title} className="h-full w-full object-cover" />
              </div>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="rounded bg-ink-800 px-1.5 py-0.5 text-[10px] font-medium uppercase text-ink-400">
                  {kindLabel}
                </span>
                <span className="text-[10px] text-ink-500">via {source}</span>
              </div>
              <h3 className="mt-1 font-semibold text-sm leading-tight text-ink-100 line-clamp-2">
                {title}
              </h3>
              {description && (
                <p className="mt-1 text-[11px] leading-relaxed text-ink-400 line-clamp-2">
                  {description}
                </p>
              )}
              <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px]">
                {episodes && (
                  <span className="rounded bg-ink-800 px-1.5 py-0.5 text-ink-300">{episodes} eps</span>
                )}
                {genres?.slice(0, 3).map((g) => (
                  <span key={g} className="rounded bg-ink-800 px-1.5 py-0.5 text-ink-400">
                    {g}
                  </span>
                ))}
                <span className="ml-auto font-mono text-sakura-400">app.mynakama.web.id</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Generate a dynamic OG image URL for social sharing.
 * Uses Nakama's own API or a simple text-to-image endpoint.
 */
export function getShareImageUrl(title: string, kind: string): string {
  const encoded = encodeURIComponent(title.slice(0, 60));
  return `https://app.mynakama.web.id/og?title=${encoded}&kind=${kind}`;
}
