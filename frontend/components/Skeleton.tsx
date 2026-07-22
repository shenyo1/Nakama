export function CardSkeleton() {
  return (
    <div className="card animate-pulse">
      <div className="aspect-[3/4] w-full rounded-lg bg-ink-800" />
      <div className="mt-2 h-3 w-3/4 rounded bg-ink-800" />
      <div className="mt-1 h-2 w-1/2 rounded bg-ink-800" />
    </div>
  );
}

export function GridSkeleton({ count = 10 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

export function MetricSkeleton() {
  return (
    <div className="card animate-pulse">
      <div className="h-3 w-20 rounded bg-ink-800" />
      <div className="mt-2 h-7 w-16 rounded bg-ink-800" />
    </div>
  );
}

export function TextSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card animate-pulse space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-3 rounded bg-ink-800" style={{ width: `${90 - i * 10}%` }} />
      ))}
    </div>
  );
}
