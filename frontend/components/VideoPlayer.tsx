"use client";

import { useState } from "react";

/**
 * VideoPlayer — renders whatever stream type the backend returns.
 *
 *  - Direct media files (.mp4/.webm/.ogg/.m3u8)         -> <video controls>
 *  - Known embed hosts (youtube, dailymotion, vimeo, ...) -> <iframe>
 *  - Everything else                                     -> clickable external link
 *
 * Many sources (samehadaku, otakudesu, anoboy) only expose embed/iframe URLs
 * or JS-decoded player tokens rather than clean .mp4 files, so a single
 * universal player isn't possible. This component degrades gracefully: it
 * plays what it can inline and hands the rest off as a link.
 */
interface VideoPlayerProps {
  url?: string | null;
  quality?: string | null;
  host?: string | null;
  poster?: string | null;
}

const DIRECT_RE = /\.(mp4|webm|ogg|ogv|m4v|m3u8)(\?|#|$)/i;

const EMBED_HOSTS: Array<[RegExp, (u: string) => string]> = [
  [
    /(?:youtube\.com|youtu\.be)/i,
    (u) => {
      const id =
        u.match(/v=([\w-]{6,})/)?.[1] || u.match(/youtu\.be\/([\w-]{6,})/)?.[1] || "";
      return id ? `https://www.youtube.com/embed/${id}` : u;
    },
  ],
  [
    /dailymotion\.com/i,
    (u) => {
      const id = u.match(/\/video\/([\w]+)/)?.[1] || "";
      return id ? `https://www.dailymotion.com/embed/video/${id}` : u;
    },
  ],
  [
    /vimeo\.com/i,
    (u) => {
      const id = u.match(/vimeo\.com\/(\d+)/)?.[1] || "";
      return id ? `https://player.vimeo.com/video/${id}` : u;
    },
  ],
];

function embedUrl(url: string): string {
  for (const [re, to] of EMBED_HOSTS) {
    if (re.test(url)) return to(url);
  }
  return url;
}

export default function VideoPlayer({ url, quality, host, poster }: VideoPlayerProps) {
  const [failed, setFailed] = useState(false);

  if (!url) return null;

  // Direct video file -> native <video>
  if (DIRECT_RE.test(url) && !failed) {
    return (
      <div className="card overflow-hidden">
        <video
          className="w-full aspect-video bg-black"
          src={url}
          controls
          playsInline
          preload="metadata"
          poster={poster || undefined}
          onError={() => setFailed(true)}
        >
          Your browser does not support HTML5 video.
        </video>
        <div className="flex items-center justify-between px-3 py-2 text-xs text-ink-400">
          <span>
            {host || "Video"}
            {quality ? ` · ${quality}` : ""}
          </span>
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            className="text-sakura-400 hover:underline"
          >
            Open in new tab
          </a>
        </div>
      </div>
    );
  }

  // Embeddable host -> iframe (e.g. samehadaku blogger player, youtube, ...)
  const emb = embedUrl(url);
  return (
    <div className="card overflow-hidden">
      <div className="aspect-video bg-black">
        <iframe
          className="h-full w-full"
          src={emb}
          title={host || "Embedded player"}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
        />
      </div>
      <div className="flex items-center justify-between px-3 py-2 text-xs text-ink-400">
        <span>
          {host || "Embedded player"}
          {quality ? ` · ${quality}` : ""}
        </span>
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="text-sakura-400 hover:underline"
        >
          Open on source
        </a>
      </div>
    </div>
  );
}
