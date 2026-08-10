import { imageProxyUrl } from "@/lib/api";

type Props = {
  title: string;
  subtitle?: string;
  thumbnail?: string;
  href?: string;
  badge?: string;
  source?: string;
  kind?: string;
  slug?: string;
};

export function ItemCard({ title, subtitle, thumbnail, href, badge, source, kind, slug }: Props) {
  // Build INTERNAL detail link whenever source + kind + slug are present.
  // Prefer it over the raw external href (it.url points at the origin site),
  // so cards navigate within Nakama instead of redirecting to the source.
  let internalHref = "";
  if (source && kind && slug) {
    if (kind === "comic") internalHref = `/comic/${source}/manga/${slug}`;
    else if (kind === "anime") internalHref = `/anime/${source}/detail/${slug}`;
    else if (kind === "novel") internalHref = `/novel/${source}/detail/${slug}`;
    else internalHref = href || "";
  } else {
    internalHref = href || "";
  }

  const inner = (
    <article className="card card-hover group flex h-full flex-col gap-2 sm:gap-3 overflow-hidden">
      <div className="relative aspect-[3/4] w-full overflow-hidden rounded-lg bg-ink-800">
        {thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageProxyUrl(thumbnail)}
            alt={title}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-110"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-ink-500">
            <span className="text-2xl opacity-30">📚</span>
          </div>
        )}
        {/* Gradient overlay on hover */}
        <div className="absolute inset-0 bg-gradient-to-t from-ink-950/80 via-transparent to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
        {badge ? (
          <span className="absolute left-1.5 top-1.5 rounded-md bg-sakura-500/90 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-white shadow-lg backdrop-blur sm:left-2 sm:top-2 sm:px-2 sm:text-[10px]">
            {badge}
          </span>
        ) : null}
        {/* Source badge bottom-right */}
        {source ? (
          <span className="absolute bottom-1.5 right-1.5 rounded-md bg-ink-950/80 px-1.5 py-0.5 text-[8px] font-mono text-ink-300 backdrop-blur sm:bottom-2 sm:right-2 sm:text-[9px]">
            {source}
          </span>
        ) : null}
      </div>
      <div className="min-w-0">
        <h3 className="truncate text-xs font-semibold text-ink-50 transition-colors group-hover:text-sakura-300 sm:text-sm">{title}</h3>
        {subtitle ? (
          <p className="mt-0.5 truncate text-[10px] text-ink-400 sm:text-xs">{subtitle}</p>
        ) : null}
      </div>
    </article>
  );

  if (internalHref) {
    return (
      <a href={internalHref} className="block h-full">
        {inner}
      </a>
    );
  }
  return inner;
}
