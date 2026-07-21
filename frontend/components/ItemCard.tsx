type Props = {
  title: string;
  subtitle?: string;
  thumbnail?: string;
  href?: string;
  badge?: string;
};

export function ItemCard({ title, subtitle, thumbnail, href, badge }: Props) {
  const inner = (
    <article className="card card-hover flex h-full flex-col gap-3">
      <div className="relative aspect-[3/4] w-full overflow-hidden rounded-lg bg-ink-800">
        {thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={thumbnail}
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
          <span className="absolute left-2 top-2 rounded bg-sakura-500/90 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
            {badge}
          </span>
        ) : null}
      </div>
      <div className="min-w-0">
        <h3 className="truncate text-sm font-semibold text-ink-50">{title}</h3>
        {subtitle ? (
          <p className="mt-0.5 truncate text-xs text-ink-400">{subtitle}</p>
        ) : null}
      </div>
    </article>
  );

  if (href) {
    return (
      <a href={href} target="_blank" rel="noreferrer" className="block h-full">
        {inner}
      </a>
    );
  }
  return inner;
}
