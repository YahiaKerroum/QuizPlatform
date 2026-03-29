"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { QuestionCard } from "@/components/quiz/QuestionCard";
import { QuizProgress } from "@/components/quiz/QuizProgress";
import { QuizTimer } from "@/components/quiz/QuizTimer";
import { Button } from "@/components/ui/Button";
import { Toast } from "@/components/ui/Toast";
import { useQuiz } from "@/hooks/useQuiz";
import { useTimer } from "@/hooks/useTimer";
import type { SessionStartOut } from "@/lib/types";

export default function QuizPage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [initialData, setInitialData] = useState<SessionStartOut | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem("session_start");
    if (!raw) {
      router.replace("/dashboard");
      return;
    }
    try {
      const parsed = JSON.parse(raw) as SessionStartOut;
      if (parsed.session_id !== params.sessionId) {
        router.replace("/dashboard");
        return;
      }
      setInitialData(parsed);
    } catch {
      router.replace("/dashboard");
    }
  }, [params.sessionId, router]);

  if (!initialData) return null;

  return <QuizSessionView initialData={initialData} sessionId={params.sessionId} />;
}

function QuizSessionView({
  initialData,
  sessionId,
}: {
  initialData: SessionStartOut;
  sessionId: string;
}) {
  const router = useRouter();
  const quiz = useQuiz(initialData);
  const elapsed = useTimer(quiz.state.questionNumber);

  useEffect(() => {
    if (quiz.state.done) {
      router.replace(`/result/${sessionId}`);
    }
  }, [quiz.state.done, router, sessionId]);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex-1">
          <QuizProgress value={quiz.state.questionNumber} total={quiz.state.total} />
        </div>
        <QuizTimer elapsed={elapsed} />
      </div>
      {quiz.state.error ? <div className="mb-4"><Toast message={quiz.state.error} tone="error" /></div> : null}
      <QuestionCard
        question={quiz.state.currentQuestion}
        selected={quiz.state.selected}
        disabled={quiz.state.submitting}
        onSelect={quiz.selectAnswer}
      />
      {quiz.state.selected ? (
        <div className="mt-6 flex justify-end">
          <Button
            variant="secondary"
            disabled={quiz.state.submitting}
            onClick={() => void quiz.confirmAnswer(Date.now() - quiz.questionRenderTime)}
          >
            {quiz.state.submitting ? "Submitting..." : "Confirm Answer"}
          </Button>
        </div>
      ) : null}
    </main>
  );
}
