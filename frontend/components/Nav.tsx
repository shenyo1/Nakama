"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LanguageToggle } from "../lib/i18n";

const publicLinks = [
  { href: "/", label: "Home" },
  { href: "/anime", label: "Anime" },
  { href: "/comic", label: "Comic" },
  { href: "/novel", label: "Novel" },
  { href: "/search", label: "Search" },
  { href: "/status", label: "Status" },
];

const authedLinks = [
  ...publicLinks,
  { href: "/history", label: "History" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/analytics", label: "Analytics" },
  { href: "/ws-test", label: "Live WS" },
];

interface UserInfo {
  username?: string;
  id?: number;
}

export function Nav() {
  const [authed, setAuthed] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [mounted, setMounted] = useState(false);
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

  const links = authed ? authedLinks : publicLinks;

  return (
    <header className="sticky top-0 z-40 border-b border-ink-700/50 bg-ink-950/80 backdrop-blur">
      <div className="container-page flex h-14 items-center justify-between gap-4">
        <Link href="/" className="font-display text-lg font-bold tracking-tight shrink-0">
          <span className="text-sakura-400">Nakama</span>
        </Link>
        <nav className="flex items-center gap-1 overflow-x-auto scrollbar-hide sm:gap-2" aria-label="Main navigation">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`whitespace-nowrap rounded-md px-2.5 py-1.5 text-sm hover:bg-ink-800 hover:text-white ${
                pathname === l.href ? "bg-ink-800 text-white" : "text-ink-200"
              }`}
            >
              {l.label}
            </Link>
          ))}
          <LanguageToggle />
          {/* Auth area: avoid hydration mismatch by rendering after mount */}
          {mounted && authed ? (
            <>
              {user?.username && (
                <span className="whitespace-nowrap px-2 py-1 text-xs text-ink-400" aria-label="Logged in user">
                  {user.username}
                </span>
              )}
              <button
                onClick={handleLogout}
                className="whitespace-nowrap rounded-md px-2.5 py-1.5 text-sm text-rose-400 hover:bg-ink-800"
                aria-label="Logout"
              >
                Logout
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="whitespace-nowrap rounded-md px-2.5 py-1.5 text-sm text-sakura-400 hover:bg-ink-800"
            >
              Login
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
