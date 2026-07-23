import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Nav } from "../components/Nav";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { I18nProvider } from "../lib/i18n";

export const metadata: Metadata = {
  title: "Nakama",
  description:
    "Nakama: multi-source anime, comic, and novel REST API with live WebSocket updates.",
  manifest: "/manifest.json",
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
    <html lang="en" className="dark">
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
            Powered by{" "}
            <a
              className="text-sakura-400 hover:underline"
              href="https://github.com/shenyo1/Nakama"
              target="_blank"
              rel="noreferrer"
            >
              shenyo1/Nakama
            </a>{" "}
            · Nakama FastAPI backend
          </footer>
        </I18nProvider>
      </body>
    </html>
  );
}
