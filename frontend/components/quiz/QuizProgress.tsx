import { ProgressBar } from "@/components/ui/ProgressBar";

export function QuizProgress({ value, total }: { value: number; total: number }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm text-ink/75">
        <span className="font-semibold">Question {value} of {total}</span>
        <span>{Math.round((value / total) * 100)}%</span>
      </div>
      <ProgressBar value={value} total={total} />
    </div>
  );
}

