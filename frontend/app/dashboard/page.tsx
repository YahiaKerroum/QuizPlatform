"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { QuizCard } from "@/components/dashboard/QuizCard";
import { SessionHistory } from "@/components/dashboard/SessionHistory";
import { Card } from "@/components/ui/Card";
import { Toast } from "@/components/ui/Toast";
import api from "@/lib/api";
import type { QuizSummaryOut, SessionHistoryOut, SessionStartOut } from "@/lib/types";

export default function DashboardPage() {
  const router = useRouter();
  const [quizzes, setQuizzes] = useState<QuizSummaryOut[]>([]);
  const [history, setHistory] = useState<SessionHistoryOut[]>([]);
  const [loadingQuizId, setLoadingQuizId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [quizzesResponse, historyResponse] = await Promise.all([
          api.get<QuizSummaryOut[]>("/quizzes"),
          api.get<SessionHistoryOut[]>("/sessions/history"),
        ]);
        setQuizzes(quizzesResponse.data);
        setHistory(historyResponse.data);
      } catch {
        setError("Could not load the dashboard.");
      }
    }

    void loadDashboard();
  }, []);

  async function startSession(quizId: string) {
    setLoadingQuizId(quizId);
    setError(null);

    try {
      const { data } = await api.post<SessionStartOut>("/sessions", { quiz_id: quizId });
      sessionStorage.setItem("session_start", JSON.stringify(data));
      router.push(`/quiz/${data.session_id}`);
    } catch {
      setError("Could not start the quiz session.");
    } finally {
      setLoadingQuizId(null);
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <section className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-clay">Dashboard</p>
          <h1 className="mt-3 font-heading text-5xl text-ink">Choose a quiz and answer it one question at a time.</h1>
        </div>
      </section>
      {error ? <Toast message={error} tone="error" /> : null}
      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {quizzes.map((quiz) => (
          <QuizCard
            key={quiz.id}
            quiz={quiz}
            loading={loadingQuizId === quiz.id}
            onStart={startSession}
          />
        ))}
      </section>
      <section className="mt-10">
        {history.length > 0 ? (
          <SessionHistory sessions={history} />
        ) : (
          <Card>
            <h2 className="font-heading text-2xl text-ink">Past Sessions</h2>
            <p className="mt-2 text-sm text-ink/70">Your attempts will appear here after you complete a quiz.</p>
          </Card>
        )}
      </section>
    </main>
  );
}

