import { ItemCard } from "./ItemCard";
import type { UnifiedItem } from "@/lib/api";

/**
 * Grid for the aggregated /{kind}/all/home feed. Unlike SourceGrid, each
 * item carries its own `_best_source` (the provider chosen when the title
 * is duplicated across sources), so the internal link is built per-item
 * instead of from one page-wide `source` prop. Items backed by more than
 * one provider get a small "N sources" badge — that's the only place the
 * provider concept surfaces to the user; picking a provider is not required.
 */
export function UnifiedGrid({
  items,
  empty = "No items returned.",
  kind,
}: {
  items: UnifiedItem[];
  empty?: string;
  kind: string;
}) {
  if (!items.length) {
    return <div className="card text-sm text-ink-400">{empty}</div>;
  }
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {items.map((it, i) => {
        const count = it._source_count ?? it._sources?.length ?? 1;
        return (
          <ItemCard
            key={`${it.slug || it.title || i}`}
            title={String(it.title || it.slug || "Untitled")}
            subtitle={it.slug ? String(it.slug) : undefined}
            thumbnail={typeof it.thumbnail === "string" ? it.thumbnail : undefined}
            href={typeof it.url === "string" ? it.url : undefined}
            source={it._best_source}
            kind={kind}
            slug={typeof it.slug === "string" ? it.slug : undefined}
            badge={count > 1 ? `${count} sumber` : undefined}
          />
        );
      })}
    </div>
  );
}
