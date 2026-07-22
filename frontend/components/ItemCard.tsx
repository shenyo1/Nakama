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
  // Build internal detail link if source + kind + slug available
  let internalHref = href;
  if (!internalHref && source && kind && slug) {
    if (kind === "comic") internalHref = `/comic/${source}/manga/${slug}`;
    else if (kind === "anime") internalHref = `/anime/${source}/detail/${slug}`;
    else if (kind === "novel") internalHref = `/novel/${source}/detail/${slug}`;
  }

  const inner = (
    <article className="card card-hover flex h-full flex-col gap-2 sm:gap-3">
      <div className="relative aspect-[3/4] w-full overflow-hidden rounded-lg bg-ink-800">
        {thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={`/api/backend/image?url=${encodeURIComponent(thumbnail)}`}
            alt={title}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-ink-400">
            no cover
          </div>
        )}
        {badge ? (
          <span className="absolute left-1.5 top-1.5 rounded bg-sakura-500/90 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-white sm:left-2 sm:top-2 sm:px-2 sm:text-[10px]">
            {badge}
          </span>
        ) : null}
      </div>
      <div className="min-w-0">
        <h3 className="truncate text-xs font-semibold text-ink-50 sm:text-sm">{title}</h3>
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
