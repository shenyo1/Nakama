import { ItemCard } from "./ItemCard";

type Item = {
  title?: string;
  slug?: string;
  thumbnail?: string;
  url?: string;
  [k: string]: unknown;
};

export function SourceGrid({
  items,
  empty = "No items returned.",
}: {
  items: Item[];
  empty?: string;
}) {
  if (!items.length) {
    return (
      <div className="card text-sm text-ink-400">{empty}</div>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {items.map((it, i) => (
        <ItemCard
          key={`${it.slug || it.title || i}`}
          title={String(it.title || it.slug || "Untitled")}
          subtitle={it.slug ? String(it.slug) : undefined}
          thumbnail={typeof it.thumbnail === "string" ? it.thumbnail : undefined}
          href={typeof it.url === "string" ? it.url : undefined}
        />
      ))}
    </div>
  );
}
