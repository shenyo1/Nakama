"use client";

import { useState } from "react";

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

  const kindEmoji = kind === "anime" ? "🎬" : kind === "comic" ? "📚" : "📖";
  const kindLabel = kind === "anime" ? "Anime" : kind === "comic" ? "Comic" : "Novel";

  // Share targets
  const shareTwitter = () => {
    const text = `${kindEmoji} Reading: ${title}\n\n${description ? description.slice(0, 100) + "..." : ""}\n\nRead on Nakama: ${url}`;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`, "_blank");
  };

  const shareTelegram = () => {
    const text = `${kindEmoji} *${title}*\n\n${description ? description.slice(0, 150) + "..." : ""}\n\n[Read on Nakama](${url})`;
    window.open(`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`, "_blank");
  };

  const shareWhatsApp = () => {
    const text = `${kindEmoji} ${title}\n\n${description ? description.slice(0, 150) + "..." : ""}\n\n${url}`;
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
          title: `${kindEmoji} ${title}`,
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
          className="flex items-center gap-1 rounded-full bg-sakura-500/20 px-3 py-1.5 text-xs font-medium text-sakura-400 hover:bg-sakura-500/30 transition-colors"
        >
          📤 Share
        </button>
        <button
          onClick={shareTwitter}
          className="flex items-center gap-1 rounded-full bg-ink-800 px-3 py-1.5 text-xs font-medium text-ink-200 hover:bg-ink-700 transition-colors"
        >
          𝕏 Tweet
        </button>
        <button
          onClick={shareTelegram}
          className="flex items-center gap-1 rounded-full bg-ink-800 px-3 py-1.5 text-xs font-medium text-ink-200 hover:bg-ink-700 transition-colors"
        >
          ✈️ Telegram
        </button>
        <button
          onClick={shareWhatsApp}
          className="flex items-center gap-1 rounded-full bg-ink-800 px-3 py-1.5 text-xs font-medium text-ink-200 hover:bg-ink-700 transition-colors"
        >
          💬 WA
        </button>
        <button
          onClick={copyLink}
          className="flex items-center gap-1 rounded-full bg-ink-800 px-3 py-1.5 text-xs font-medium text-ink-200 hover:bg-ink-700 transition-colors"
        >
          {copied ? "✅ Copied!" : "🔗 Copy"}
        </button>
        <button
          onClick={() => setShowPreview(!showPreview)}
          className="flex items-center gap-1 rounded-full bg-ink-800 px-3 py-1.5 text-xs font-medium text-ink-200 hover:bg-ink-700 transition-colors"
        >
          🖼️ Preview
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
                <span className="text-xs">{kindEmoji}</span>
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
                <span className="ml-auto font-mono text-sakura-400">mynakama.web.id</span>
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
