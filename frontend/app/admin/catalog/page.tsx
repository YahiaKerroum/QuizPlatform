"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { Toast } from "@/components/ui/Toast";
import api from "@/lib/api";
import type { AdminQuizDetailOut, ModuleOut, QuizSummaryOut, QuizUpsertIn } from "@/lib/types";

const defaultQuestions = JSON.stringify(
  [
    {
      question_number: 1,
      question_text: "What does this quiz open with?",
      question_image_url: null,
      choice_a: "A first option",
      choice_a_image_url: null,
      choice_b: "A second option",
      choice_b_image_url: null,
      choice_c: null,
      choice_c_image_url: null,
      choice_d: null,
      choice_d_image_url: null,
      choice_e: null,
      choice_e_image_url: null,
      choice_f: null,
      choice_f_image_url: null,
      correct_answer: "a",
      difficulty: null,
    },
  ],
  null,
  2,
);

function summarizeError(error: unknown, fallback: string) {
  if (typeof error === "object" && error && "response" in error) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

export default function AdminCatalogPage() {
  const [modules, setModules] = useState<ModuleOut[]>([]);
  const [quizzes, setQuizzes] = useState<QuizSummaryOut[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [moduleMode, setModuleMode] = useState<"create" | "edit">("create");
  const [moduleForm, setModuleForm] = useState({
    id: "",
    display_name: "",
    description: "",
  });
  const [quizMode, setQuizMode] = useState<"create" | "edit">("create");
  const [quizForm, setQuizForm] = useState({
    id: "",
    display_name: "",
    module_id: "",
    questionsJson: defaultQuestions,
  });

  async function loadCatalog() {
    const [modulesResponse, quizzesResponse] = await Promise.all([
      api.get<ModuleOut[]>("/admin/modules"),
      api.get<QuizSummaryOut[]>("/admin/quizzes"),
    ]);
    setModules(modulesResponse.data);
    setQuizzes(quizzesResponse.data);
  }

  useEffect(() => {
    void loadCatalog().catch(() => {
      setMessage("Could not load the catalog.");
    });
  }, []);

  function resetModuleForm() {
    setModuleMode("create");
    setModuleForm({ id: "", display_name: "", description: "" });
  }

  function resetQuizForm() {
    setQuizMode("create");
    setQuizForm({
      id: "",
      display_name: "",
      module_id: "",
      questionsJson: defaultQuestions,
    });
  }

  async function submitModule() {
    setLoading(true);
    setMessage(null);

    try {
      if (moduleMode === "create") {
        await api.post("/admin/modules", {
          id: moduleForm.id,
          display_name: moduleForm.display_name,
          description: moduleForm.description || null,
        });
      } else {
        await api.put(`/admin/modules/${moduleForm.id}`, {
          display_name: moduleForm.display_name,
          description: moduleForm.description || null,
        });
      }

      await loadCatalog();
      setMessage(moduleMode === "create" ? "Module created." : "Module updated.");
      resetModuleForm();
    } catch (error) {
      setMessage(summarizeError(error, "Could not save the module."));
    } finally {
      setLoading(false);
    }
  }

  async function loadQuizIntoForm(quizId: string) {
    setLoading(true);
    setMessage(null);

    try {
      const { data } = await api.get<AdminQuizDetailOut>(`/admin/quizzes/${quizId}`);
      setQuizMode("edit");
      setQuizForm({
        id: data.id,
        display_name: data.display_name,
        module_id: data.module_id ?? "",
        questionsJson: JSON.stringify(data.questions, null, 2),
      });
    } catch (error) {
      setMessage(summarizeError(error, "Could not load the quiz."));
    } finally {
      setLoading(false);
    }
  }

  async function submitQuiz() {
    setLoading(true);
    setMessage(null);

    try {
      const payload: QuizUpsertIn = {
        id: quizForm.id,
        display_name: quizForm.display_name,
        module_id: quizForm.module_id || null,
        questions: JSON.parse(quizForm.questionsJson),
      };

      if (quizMode === "create") {
        await api.post("/admin/quizzes", payload);
      } else {
        await api.put(`/admin/quizzes/${quizForm.id}`, payload);
      }

      await loadCatalog();
      setMessage(quizMode === "create" ? "Quiz created." : "Quiz updated.");
      resetQuizForm();
    } catch (error) {
      setMessage(summarizeError(error, "Could not save the quiz. Make sure the questions JSON is valid."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
      <div className="space-y-6">
        <Card className="space-y-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="font-heading text-3xl text-ink">Modules</h2>
              <p className="mt-2 text-sm text-ink/70">Group quizzes into domains like C Development or Machine Learning.</p>
            </div>
            {moduleMode === "edit" ? (
              <Button variant="ghost" onClick={resetModuleForm}>
                New module
              </Button>
            ) : null}
          </div>
          <div className="grid gap-4">
            <Input
              placeholder="Module id, for example c-development"
              value={moduleForm.id}
              disabled={moduleMode === "edit"}
              onChange={(event) => setModuleForm((current) => ({ ...current, id: event.target.value }))}
            />
            <Input
              placeholder="Display name"
              value={moduleForm.display_name}
              onChange={(event) => setModuleForm((current) => ({ ...current, display_name: event.target.value }))}
            />
            <Textarea
              placeholder="Short description for this module"
              value={moduleForm.description}
              onChange={(event) => setModuleForm((current) => ({ ...current, description: event.target.value }))}
            />
            <Button variant="secondary" disabled={loading} onClick={() => void submitModule()}>
              {loading ? "Saving..." : moduleMode === "create" ? "Create module" : "Update module"}
            </Button>
          </div>
        </Card>
        <Card className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <h3 className="font-heading text-2xl text-ink">Existing modules</h3>
            <p className="text-sm text-ink/55">{modules.length} total</p>
          </div>
          <div className="space-y-3">
            {modules.map((module) => (
              <button
                key={module.id}
                type="button"
                className="w-full rounded-[1.5rem] border border-ink/10 bg-white/70 px-4 py-4 text-left transition hover:-translate-y-0.5 hover:border-clay/35"
                onClick={() => {
                  setModuleMode("edit");
                  setModuleForm({
                    id: module.id,
                    display_name: module.display_name,
                    description: module.description ?? "",
                  });
                }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-semibold text-ink">{module.display_name}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.2em] text-clay">{module.id}</p>
                    <p className="mt-2 text-sm text-ink/65">{module.description ?? "No description yet."}</p>
                  </div>
                  <div className="rounded-full bg-clay/10 px-3 py-1 text-xs font-semibold text-clay">
                    {module.quiz_count} quizzes
                  </div>
                </div>
              </button>
            ))}
            {modules.length === 0 ? <p className="text-sm text-ink/60">No modules created yet.</p> : null}
          </div>
        </Card>
      </div>

      <div className="space-y-6">
        <Card className="space-y-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="font-heading text-3xl text-ink">Quiz Catalog</h2>
              <p className="mt-2 text-sm text-ink/70">Create quizzes, edit questions, and assign each quiz to a module.</p>
            </div>
            {quizMode === "edit" ? (
              <Button variant="ghost" onClick={resetQuizForm}>
                New quiz
              </Button>
            ) : null}
          </div>
          <div className="grid gap-4">
            <Input
              placeholder="Quiz id"
              value={quizForm.id}
              disabled={quizMode === "edit"}
              onChange={(event) => setQuizForm((current) => ({ ...current, id: event.target.value }))}
            />
            <Input
              placeholder="Quiz display name"
              value={quizForm.display_name}
              onChange={(event) => setQuizForm((current) => ({ ...current, display_name: event.target.value }))}
            />
            <select
              className="w-full rounded-3xl border border-ink/15 bg-white/82 px-4 py-3 text-sm text-ink outline-none transition duration-300 ease-out hover:border-ink/25 focus:border-clay"
              value={quizForm.module_id}
              onChange={(event) => setQuizForm((current) => ({ ...current, module_id: event.target.value }))}
            >
              <option value="">No module</option>
              {modules.map((module) => (
                <option key={module.id} value={module.id}>
                  {module.display_name}
                </option>
              ))}
            </select>
            <Textarea
              placeholder="Questions JSON array"
              value={quizForm.questionsJson}
              onChange={(event) => setQuizForm((current) => ({ ...current, questionsJson: event.target.value }))}
            />
            <p className="text-xs leading-6 text-ink/55">
              The editor expects a JSON array of question objects with `question_number`, answer choices, `correct_answer`, optional image URLs, and optional `difficulty`.
            </p>
            <Button variant="secondary" disabled={loading} onClick={() => void submitQuiz()}>
              {loading ? "Saving..." : quizMode === "create" ? "Create quiz" : "Update quiz"}
            </Button>
          </div>
        </Card>
        <Card className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <h3 className="font-heading text-2xl text-ink">Existing quizzes</h3>
            <p className="text-sm text-ink/55">{quizzes.length} total</p>
          </div>
          <div className="space-y-3">
            {quizzes.map((quiz) => (
              <button
                key={quiz.id}
                type="button"
                className="w-full rounded-[1.5rem] border border-ink/10 bg-white/70 px-4 py-4 text-left transition hover:-translate-y-0.5 hover:border-clay/35"
                onClick={() => void loadQuizIntoForm(quiz.id)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-semibold text-ink">{quiz.display_name}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.2em] text-clay">{quiz.id}</p>
                    <p className="mt-2 text-sm text-ink/65">
                      {quiz.module_display_name ?? "No module assigned"}
                    </p>
                  </div>
                  <div className="rounded-full bg-clay/10 px-3 py-1 text-xs font-semibold text-clay">
                    {quiz.question_count} questions
                  </div>
                </div>
              </button>
            ))}
            {quizzes.length === 0 ? <p className="text-sm text-ink/60">No quizzes created yet.</p> : null}
          </div>
        </Card>
      </div>
      {message ? <Toast message={message} tone={message.toLowerCase().includes("could not") ? "error" : "success"} /> : null}
    </section>
  );
}
