export function ProgressBar({ value, total }: { value: number; total: number }) {
  const width = total > 0 ? `${Math.min((value / total) * 100, 100)}%` : "0%";
  return (
    <div className="h-3 w-full rounded-full bg-ink/10">
      <div className="h-3 rounded-full bg-clay transition-all" style={{ width }} />
    </div>
  );
}

