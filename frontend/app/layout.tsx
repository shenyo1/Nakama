import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "../components/Nav";

export const metadata: Metadata = {
  title: "Nakama",
  description:
    "Nakama: multi-source anime, comic, and novel REST API with live WebSocket updates.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>
        <Nav />
        <main className="container-page py-8 animate-fade-in">{children}</main>
        <footer className="container-page border-t border-ink-800 py-8 text-center text-xs text-ink-500">
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
      </body>
    </html>
  );
}
