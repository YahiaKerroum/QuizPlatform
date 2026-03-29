import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { QuizSummaryOut } from "@/lib/types";

export function QuizCard({
  quiz,
  onStart,
  loading,
}: {
  quiz: QuizSummaryOut;
  onStart: (quizId: string) => void;
  loading: boolean;
}) {
  return (
    <Card className="flex h-full flex-col justify-between gap-5">
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-clay">Quiz</p>
        <h3 className="font-heading text-2xl text-ink">{quiz.display_name}</h3>
        <p className="text-sm text-ink/70">{quiz.question_count} questions</p>
      </div>
      <Button variant="secondary" disabled={loading} onClick={() => onStart(quiz.id)}>
        {loading ? "Starting..." : "Start quiz"}
      </Button>
    </Card>
  );
}

