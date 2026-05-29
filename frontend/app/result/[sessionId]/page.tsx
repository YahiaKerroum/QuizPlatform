"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { StudentLogoutButton } from "@/components/auth/StudentLogoutButton";
import { RichContent } from "@/components/content/RichContent";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Toast } from "@/components/ui/Toast";
import api from "@/lib/api";
import type { ResultOut } from "@/lib/types";

export default function ResultPage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [result, setResult] = useState<ResultOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadResult() {
      try {
        const { data } = await api.get<ResultOut>(`/sessions/${params.sessionId}/result`);
        setResult(data);
      } catch {
        setError("Could not load the result page.");
      }
    }

    void loadResult();
  }, [params.sessionId]);

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <Toast message={error} tone="error" />
      </main>
    );
  }

  if (!result) return null;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <Card className="space-y-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="space-y-3">
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-clay">Session Result</p>
            <h1 className="font-heading text-5xl text-ink">{result.correct} / {result.total}</h1>
            <p className="text-lg text-ink/70">{Math.round(result.accuracy * 100)}% accuracy</p>
          </div>
          <StudentLogoutButton />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {Object.entries(result.by_difficulty).map(([difficulty, stats]) => (
            <Card key={difficulty} className="bg-mist/70">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-clay">{difficulty}</p>
              <p className="mt-3 text-lg text-ink">{stats.correct} / {stats.total}</p>
              <p className="text-sm text-ink/70">{Math.round(stats.accuracy * 100)}% correct</p>
            </Card>
          ))}
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-ink/65">
              <tr>
                <th className="pb-3">Question</th>
                <th className="pb-3">Your answer</th>
                <th className="pb-3">Correct answer</th>
                <th className="pb-3">Correct</th>
                <th className="pb-3">Time</th>
                <th className="pb-3">Difficulty</th>
              </tr>
            </thead>
            <tbody>
              {result.by_question.map((item) => (
                <tr key={item.question_number} className="border-t border-ink/10">
                  <td className="py-3 align-top">
                    <div className="space-y-1">
                      <p className="font-semibold text-ink">Q{item.question_number}</p>
                      <div className="max-w-md text-ink/70">
                        <RichContent
                          text={item.question_text}
                          imageUrl={item.question_image_url}
                          imageAlt={`Question ${item.question_number}`}
                          compact
                        />
                      </div>
                    </div>
                  </td>
                  <td className="py-3 align-top">
                    <div className="max-w-xs space-y-2">
                      <p className="font-semibold text-ink">{item.chosen_answer.toUpperCase()}</p>
                      <RichContent
                        text={item.chosen_answer_text}
                        imageUrl={item.chosen_answer_image_url}
                        imageAlt={`Selected answer for question ${item.question_number}`}
                        compact
                      />
                    </div>
                  </td>
                  <td className="py-3 align-top">
                    <div className="max-w-xs space-y-2">
                      <p className="font-semibold text-ink">{item.correct_answer.toUpperCase()}</p>
                      <RichContent
                        text={item.correct_answer_text}
                        imageUrl={item.correct_answer_image_url}
                        imageAlt={`Correct answer for question ${item.question_number}`}
                        compact
                      />
                    </div>
                  </td>
                  <td className="py-3 align-top">{item.is_correct ? "Yes" : "No"}</td>
                  <td className="py-3 align-top">{(item.response_time_ms / 1000).toFixed(1)}s</td>
                  <td className="py-3 align-top">{item.difficulty ?? "Unassigned"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex justify-end">
          <Button variant="secondary" onClick={() => router.push("/dashboard")}>Take another quiz</Button>
        </div>
      </Card>
    </main>
  );
}
