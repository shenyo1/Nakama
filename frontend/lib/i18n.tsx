/**
 * Lightweight i18n for Nakama frontend.
 *
 * We avoid heavy libraries (next-intl, i18next) and use a simple dictionary
 * + React context. Languages: `en` (default) and `id` (Indonesian).
 *
 * Usage:
 *   import { useT } from "@/lib/i18n";
 *   const t = useT();
 *   <h1>{t("home_title")}</h1>
 */

"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Lang = "en" | "id";

const STORAGE_KEY = "nakama_lang";

export const dict = {
  en: {
    // navigation
    nav_home: "Home",
    nav_anime: "Anime",
    nav_comic: "Comic",
    nav_novel: "Novel",
    nav_search: "Search",
    nav_status: "Status",
    nav_dashboard: "Dashboard",
    nav_ws: "Live WS",
    nav_login: "Login",
    nav_history: "Continue Reading",
    nav_settings: "Settings",

    // home page
    home_title: "Nakama",
    home_subtitle: "Multi-source anime, comic, and novel REST API",
    home_browse: "Browse",
    home_total_sources: "21 public sources across anime, comic, and novel",
    home_see_dashboard: "View dashboard",
    home_see_status: "View status",

    // common
    common_loading: "Loading…",
    common_retry: "Retry",
    common_back: "Back",
    common_search: "Search",
    common_no_data: "No data",
    common_source: "Source",
    common_read: "Read",
    common_watch: "Watch",
    common_chapter: "Chapter",
    common_episode: "Episode",
    common_synopsis: "Synopsis",
    common_genres: "Genres",

    // health
    health_healthy: "Healthy",
    health_degraded: "Degraded",
    health_down: "Down",
    health_unknown: "Unknown",
    health_recovered: "Recovered",
    health_changed_to: "changed to",
  },

  id: {
    // navigation
    nav_home: "Beranda",
    nav_anime: "Anime",
    nav_comic: "Komik",
    nav_novel: "Novel",
    nav_search: "Cari",
    nav_status: "Status",
    nav_dashboard: "Dasbor",
    nav_ws: "WS Langsung",
    nav_login: "Masuk",
    nav_history: "Lanjut Baca",
    nav_settings: "Pengaturan",

    // home page
    home_title: "Nakama",
    home_subtitle: "REST API multi-sumber anime, komik, dan novel",
    home_browse: "Jelajahi",
    home_total_sources: "21 sumber publik untuk anime, komik, dan novel",
    home_see_dashboard: "Lihat dasbor",
    home_see_status: "Lihat status",

    // common
    common_loading: "Memuat…",
    common_retry: "Coba lagi",
    common_back: "Kembali",
    common_search: "Cari",
    common_no_data: "Tidak ada data",
    common_source: "Sumber",
    common_read: "Baca",
    common_watch: "Tonton",
    common_chapter: "Chapter",
    common_episode: "Episode",
    common_synopsis: "Sinopsis",
    common_genres: "Genre",

    // health
    health_healthy: "Sehat",
    health_degraded: "Terdegradasi",
    health_down: "Down",
    health_unknown: "Tidak diketahui",
    health_recovered: "Pulih",
    health_changed_to: "berubah ke",
  },
} as const;

export type Key = keyof typeof dict.en;

const I18nContext = createContext<{
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (k: Key) => string;
}>({
  lang: "en",
  setLang: () => {},
  t: (k) => dict.en[k] || k,
});

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    const saved = (typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null) as Lang | null;
    if (saved === "en" || saved === "id") setLangState(saved);
  }, []);

  function setLang(l: Lang) {
    setLangState(l);
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, l);
  }

  const value = useMemo(
    () => ({
      lang,
      setLang,
      t: (k: Key) => dict[lang][k] || dict.en[k] || String(k),
    }),
    [lang]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useT() {
  return useContext(I18nContext);
}

export function LanguageToggle() {
  const { lang, setLang } = useT();
  return (
    <button
      onClick={() => setLang(lang === "en" ? "id" : "en")}
      className="rounded-md px-2 py-1 text-xs font-mono uppercase tracking-wide text-ink-300 hover:bg-ink-800 hover:text-white"
      title={lang === "en" ? "Switch to Indonesian" : "Switch to English"}
    >
      {lang}
    </button>
  );
}
