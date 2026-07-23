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
        <I18nProvider>
          <Nav />
          <main className="container-page py-6 animate-fade-in sm:py-8">
            <ErrorBoundary>{children}</ErrorBoundary>
          </main>
          <footer className="container-page border-t border-ink-800 py-6 text-center text-xs text-ink-500 sm:py-8">
            Powered by{" "}
            <a
              className="text-sakura-400 hover:underline"
              href="https://github.com/afifghaffarr-source/Nakama"
              target="_blank"
              rel="noreferrer"
            >
              afifghaffarr-source/Nakama
            </a>{" "}
            · Nakama FastAPI backend
          </footer>
        </I18nProvider>
      </body>
    </html>
  );
}
