"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { QuizCard } from "@/components/dashboard/QuizCard";
import { SessionHistory } from "@/components/dashboard/SessionHistory";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Toast } from "@/components/ui/Toast";
import api from "@/lib/api";
import type { ModuleWithQuizzesOut, SessionHistoryOut, SessionStartOut } from "@/lib/types";

export default function DashboardPage() {
  const router = useRouter();
  const [modules, setModules] = useState<ModuleWithQuizzesOut[]>([]);
  const [history, setHistory] = useState<SessionHistoryOut[]>([]);
  const [loadingQuizId, setLoadingQuizId] = useState<string | null>(null);
  const [selectedModuleId, setSelectedModuleId] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [modulesResponse, historyResponse] = await Promise.all([
          api.get<ModuleWithQuizzesOut[]>("/quizzes/modules"),
          api.get<SessionHistoryOut[]>("/sessions/history"),
        ]);
        setModules(modulesResponse.data);
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

  const visibleModules =
    selectedModuleId === "all"
      ? modules.filter((module) => module.quizzes.length > 0)
      : modules.filter((module) => module.id === selectedModuleId && module.quizzes.length > 0);

  const totalQuizCount = modules.reduce((sum, module) => sum + module.quizzes.length, 0);

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <section className="motion-rise mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="max-w-4xl">
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-clay">Dashboard</p>
          <h1 className="mt-3 font-heading text-5xl text-ink">Choose a quiz and answer it one question at a time.</h1>
          <p className="mt-4 max-w-2xl text-lg leading-8 text-ink/72">
            Browse by module, then drop into the exact quiz you want without losing momentum.
          </p>
        </div>
        <Card className="min-w-[15rem] space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-clay">Library snapshot</p>
          <p className="font-heading text-4xl text-ink">{totalQuizCount}</p>
          <p className="text-sm text-ink/68">quizzes across {modules.length} module groups</p>
        </Card>
      </section>
      {error ? <Toast message={error} tone="error" /> : null}
      {modules.length > 0 ? (
        <section className="motion-rise motion-delay-1 mb-8 flex flex-wrap gap-3">
          <Button variant={selectedModuleId === "all" ? "secondary" : "ghost"} onClick={() => setSelectedModuleId("all")}>
            All modules
          </Button>
          {modules
            .filter((module) => module.quizzes.length > 0)
            .map((module) => (
              <Button
                key={module.id}
                variant={selectedModuleId === module.id ? "secondary" : "ghost"}
                onClick={() => setSelectedModuleId(module.id)}
              >
                {module.display_name}
              </Button>
            ))}
        </section>
      ) : null}
      <section className="motion-rise motion-delay-1 space-y-10">
        {visibleModules.map((module) => (
          <section key={module.id} className="space-y-5">
            <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-clay">Module</p>
                <h2 className="mt-2 font-heading text-3xl text-ink">{module.display_name}</h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-ink/68">
                  {module.description ?? "A grouped set of quizzes in the same domain."}
                </p>
              </div>
              <p className="text-sm text-ink/55">{module.quizzes.length} quizzes</p>
            </div>
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {module.quizzes.map((quiz) => (
                <QuizCard
                  key={quiz.id}
                  quiz={quiz}
                  loading={loadingQuizId === quiz.id}
                  onStart={startSession}
                />
              ))}
            </div>
          </section>
        ))}
        {visibleModules.length === 0 ? (
          <Card>
            <h2 className="font-heading text-2xl text-ink">No quizzes in this module yet</h2>
            <p className="mt-2 text-sm text-ink/70">Pick a different module or create quizzes from the admin catalog.</p>
          </Card>
        ) : null}
      </section>
      <section className="motion-rise motion-delay-2 mt-10">
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
