import Link from "next/link";

const links = [
  { href: "/", label: "Home" },
  { href: "/anime", label: "Anime" },
  { href: "/comic", label: "Comic" },
  { href: "/novel", label: "Novel" },
  { href: "/search", label: "Search" },
  { href: "/status", label: "Status" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/ws-test", label: "Live WS" },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-ink-700/50 bg-ink-950/80 backdrop-blur">
      <div className="container-page flex h-14 items-center justify-between gap-4">
        <Link href="/" className="font-display text-lg font-bold tracking-tight shrink-0">
          <span className="text-sakura-400">Nakama</span>
        </Link>
        <nav className="flex items-center gap-1 overflow-x-auto scrollbar-hide sm:gap-2">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="whitespace-nowrap rounded-md px-2.5 py-1.5 text-sm text-ink-200 hover:bg-ink-800 hover:text-white"
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
