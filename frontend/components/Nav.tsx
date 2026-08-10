"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LanguageToggle } from "../lib/i18n";
import {
  IconHome,
  IconDeviceTv,
  IconBooks,
  IconBook,
  IconSparkles,
  IconBrush,
  IconSearch,
  IconHeartbeat,
  IconClockHour4,
  IconChartBar,
  IconPencil,
} from "@tabler/icons-react";

const publicLinks = [
  { href: "/", label: "Home", Icon: IconHome },
  { href: "/anime", label: "Anime", Icon: IconDeviceTv },
  { href: "/comic", label: "Comic", Icon: IconBooks },
  { href: "/novel", label: "Novel", Icon: IconBook },
  { href: "/originals", label: "Originals", Icon: IconSparkles },
  { href: "/ai-comic", label: "AI Comic", Icon: IconBrush },
  { href: "/search", label: "Search", Icon: IconSearch },
  { href: "/status", label: "Status", Icon: IconHeartbeat },
];

const authedExtraLinks = [
  { href: "/history", label: "History", Icon: IconClockHour4 },
  { href: "/dashboard", label: "Dashboard", Icon: IconChartBar },
  { href: "/creator", label: "Creator", Icon: IconPencil },
];

interface UserInfo {
  username?: string;
  id?: number;
}

export function Nav() {
  const [authed, setAuthed] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [mounted, setMounted] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    setMounted(true);
    try {
      const token = localStorage.getItem("nakama_token");
      const raw = localStorage.getItem("nakama_user");
      if (token) {
        setAuthed(true);
        if (raw) setUser(JSON.parse(raw));
      } else {
        setAuthed(false);
        setUser(null);
      }
    } catch {
      setAuthed(false);
    }
  }, [pathname]);

  function handleLogout() {
    localStorage.removeItem("nakama_token");
    localStorage.removeItem("nakama_user");
    setAuthed(false);
    setUser(null);
    router.push("/");
  }

  const links = authed ? [...publicLinks, ...authedExtraLinks] : publicLinks;

  return (
    <header className="sticky top-0 z-40 border-b border-ink-700/50 bg-ink-950/90 backdrop-blur-lg">
      <div className="container-page flex h-14 items-center justify-between gap-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 font-display text-lg font-bold tracking-tight shrink-0 group">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-sakura-500 to-sakura-700 text-white shadow-lg shadow-sakura-500/20 transition-transform group-hover:scale-110">
            <IconSparkles size={16} />
          </span>
          <span className="text-sakura-400">Nakama</span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-1 overflow-x-auto scrollbar-hide" aria-label="Main navigation">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`whitespace-nowrap rounded-lg px-2.5 py-1.5 text-sm transition-all ${
                pathname === l.href
                  ? "bg-sakura-500/15 text-sakura-300 font-medium"
                  : "text-ink-200 hover:bg-ink-800 hover:text-white"
              }`}
            >
              {l.label}
            </Link>
          ))}
          <LanguageToggle />
          {mounted && authed ? (
            <>
              {user?.username && (
                <span className="whitespace-nowrap px-2 py-1 text-xs text-ink-400" aria-label="Logged in user">
                  {user.username}
                </span>
              )}
              <button
                onClick={handleLogout}
                className="whitespace-nowrap rounded-lg px-2.5 py-1.5 text-sm text-rose-400 hover:bg-rose-500/10 transition-colors"
                aria-label="Logout"
              >
                Logout
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="whitespace-nowrap rounded-lg px-2.5 py-1.5 text-sm text-sakura-400 hover:bg-sakura-500/10 transition-colors"
            >
              Login
            </Link>
          )}
        </nav>

        {/* Mobile menu button */}
        <button
          className="md:hidden flex items-center justify-center rounded-lg p-2 text-ink-200 hover:bg-ink-800"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
          aria-expanded={menuOpen}
        >
          {menuOpen ? (
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </div>

      {/* Mobile dropdown */}
      {menuOpen && (
        <nav className="md:hidden border-t border-ink-700/50 bg-ink-950/95 backdrop-blur-lg animate-fade-in" aria-label="Mobile navigation">
          <div className="container-page py-3 grid grid-cols-3 gap-1">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                onClick={() => setMenuOpen(false)}
                className={`flex flex-col items-center gap-1 rounded-lg px-2 py-2 text-xs transition-all ${
                  pathname === l.href
                    ? "bg-sakura-500/15 text-sakura-300"
                    : "text-ink-200 hover:bg-ink-800"
                }`}
              >
                <l.Icon size={20} stroke={1.5} />
                {l.label}
              </Link>
            ))}
          </div>
          <div className="container-page pb-3 flex items-center justify-between border-t border-ink-800 pt-3">
            <LanguageToggle />
            {mounted && authed ? (
              <button
                onClick={() => { handleLogout(); setMenuOpen(false); }}
                className="rounded-lg px-3 py-1.5 text-xs text-rose-400 hover:bg-rose-500/10"
              >
                Logout
              </button>
            ) : (
              <Link
                href="/login"
                onClick={() => setMenuOpen(false)}
                className="rounded-lg px-3 py-1.5 text-xs text-sakura-400 hover:bg-sakura-500/10"
              >
                Login
              </Link>
            )}
          </div>
        </nav>
      )}
    </header>
  );
}
