export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-2xl bg-ink/8 ${className}`} />;
}

export function ResultPageSkeleton() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="space-y-8 rounded-[2rem] border border-white/70 bg-white/82 p-6 shadow-soft">
        <div className="space-y-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-12 w-48" />
          <Skeleton className="h-6 w-40" />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <div className="space-y-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </div>
    </main>
  );
}

export function QuizPageSkeleton() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-6">
        <Skeleton className="h-3 w-full" />
      </div>
      <div className="space-y-6 rounded-[2rem] border border-white/70 bg-white/82 p-6 shadow-soft">
        <Skeleton className="h-8 w-2/3" />
        <div className="space-y-3">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      </div>
    </main>
  );
}
