import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Nav } from "../components/Nav";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { I18nProvider } from "../lib/i18n";
import { ANIME_SOURCES, COMIC_SOURCES, NOVEL_SOURCES } from "../lib/api";

const totalSources = ANIME_SOURCES.length + COMIC_SOURCES.length + NOVEL_SOURCES.length;

// Inline service worker registration. Renders on the client after hydration.
// Avoids a separate /register-sw route and keeps the install lightweight.
const swRegister = `
if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}
`;

export const metadata: Metadata = {
  title: "Nakama. Anime, Manga & Novel Hub",
  description:
    "Browse anime, read manga, and devour novels from 21+ sources. All in one place, powered by a blazing-fast REST API.",
  manifest: "/manifest.json",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "32x32" },
      { url: "/icon-192.png", type: "image/png", sizes: "192x192" },
      { url: "/icon-512.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [{ url: "/icon-192.png", sizes: "192x192" }],
  },
  appleWebApp: {
    capable: true,
    title: "Nakama",
    statusBarStyle: "black-translucent",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#06070f",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" data-lang="en">
      <body>
        {/* Skip-to-content for keyboard/screen-reader users */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-sakura-500 focus:px-3 focus:py-2 focus:text-ink-50"
        >
          Skip to main content
        </a>
        <I18nProvider>
          <Nav />
          <main id="main-content" className="container-page py-6 animate-fade-in sm:py-8">
            <ErrorBoundary>{children}</ErrorBoundary>
          </main>
          <footer className="container-page border-t border-ink-800 py-6 text-center text-xs text-ink-500 sm:py-8">
            <div className="flex flex-col items-center gap-2">
              <div className="flex items-center gap-2">
                <span className="text-base">🌸</span>
                <span className="font-display font-bold text-ink-300">Nakama</span>
              </div>
              <p>
                Powered by{" "}
                <a
                  className="text-sakura-400 hover:underline"
                  href="https://github.com/shenyo1/Nakama"
                  target="_blank"
                  rel="noreferrer"
                >
                  shenyo1/Nakama
                </a>{" "}
                · {totalSources} sources · Anime, Manga & Novel Hub
              </p>
            </div>
          </footer>
        </I18nProvider>
        <script
          dangerouslySetInnerHTML={{ __html: swRegister }}
          suppressHydrationWarning
        />
      </body>
    </html>
  );
}
