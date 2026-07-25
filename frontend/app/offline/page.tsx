import Link from "next/link";

export const runtime = "edge";
export const dynamic = "force-static";

export default function OfflinePage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <div className="text-6xl">📡</div>
      <h1 className="text-2xl font-bold sm:text-3xl">You&apos;re offline</h1>
      <p className="max-w-md text-sm text-ink-300">
        Nakama needs a connection to fetch fresh data from comic, anime, and
        novel sources. Please check your internet and try again.
      </p>
      <Link href="/" className="btn mt-2">
        Try Again
      </Link>
    </div>
  );
}
