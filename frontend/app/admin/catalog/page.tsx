"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { Toast } from "@/components/ui/Toast";
import api from "@/lib/api";
import { summarizeFormError } from "@/lib/form";
import { moduleSchema, quizSchema } from "@/lib/validation";
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
  return summarizeFormError(error, fallback);
}

function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function createId(prefix: string): string {
  const base = slugify(prefix);
  const suffix = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}`;
  return base ? `${base}-${suffix}` : suffix;
}

export default function AdminCatalogPage() {
  const [modules, setModules] = useState<ModuleOut[]>([]);
  const [quizzes, setQuizzes] = useState<QuizSummaryOut[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [moduleMode, setModuleMode] = useState<"create" | "edit">("create");
  const [moduleForm, setModuleForm] = useState({
    id: createId("module"),
    display_name: "",
    description: "",
  });
  const [quizMode, setQuizMode] = useState<"create" | "edit">("create");
  const [quizForm, setQuizForm] = useState({
    id: createId("quiz"),
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
    setModuleForm({ id: createId("module"), display_name: "", description: "" });
  }

  function resetQuizForm() {
    setQuizMode("create");
    setQuizForm({
      id: createId("quiz"),
      display_name: "",
      module_id: "",
      questionsJson: defaultQuestions,
    });
  }

  async function submitModule() {
    setLoading(true);
    setMessage(null);

    try {
      const parsed = moduleSchema.safeParse(moduleForm);
      if (!parsed.success) {
        throw parsed.error;
      }

      if (moduleMode === "create") {
        await api.post("/admin/modules", {
          id: parsed.data.id || createId(parsed.data.display_name),
          display_name: parsed.data.display_name,
          description: parsed.data.description || null,
        });
      } else {
        await api.put(`/admin/modules/${parsed.data.id}`, {
          display_name: parsed.data.display_name,
          description: parsed.data.description || null,
        });
      }

      await loadCatalog();
      setMessage(moduleMode === "create" ? "Module created." : "Module updated.");
      resetModuleForm();
    } catch (error) {
      setMessage(`Could not save the module. ${summarizeError(error, "Check the fields and try again.")}`);
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
      setMessage(`Could not load the quiz. ${summarizeError(error, "Try again.")}`);
    } finally {
      setLoading(false);
    }
  }

  async function submitQuiz() {
    setLoading(true);
    setMessage(null);

    try {
      const parsed = quizSchema.safeParse({
        id: quizForm.id,
        display_name: quizForm.display_name,
        module_id: quizForm.module_id || null,
        questions: JSON.parse(quizForm.questionsJson),
      });
      if (!parsed.success) {
        throw parsed.error;
      }

      const payload: QuizUpsertIn = {
        id: parsed.data.id || createId(parsed.data.display_name),
        display_name: parsed.data.display_name,
        module_id: parsed.data.module_id ?? null,
        questions: parsed.data.questions.map((question) => ({
          question_number: question.question_number,
          question_text: question.question_text,
          question_image_url: question.question_image_url ?? null,
          choice_a: question.choice_a,
          choice_a_image_url: question.choice_a_image_url ?? null,
          choice_b: question.choice_b,
          choice_b_image_url: question.choice_b_image_url ?? null,
          choice_c: question.choice_c ?? null,
          choice_c_image_url: question.choice_c_image_url ?? null,
          choice_d: question.choice_d ?? null,
          choice_d_image_url: question.choice_d_image_url ?? null,
          choice_e: question.choice_e ?? null,
          choice_e_image_url: question.choice_e_image_url ?? null,
          choice_f: question.choice_f ?? null,
          choice_f_image_url: question.choice_f_image_url ?? null,
          correct_answer: question.correct_answer,
          difficulty: question.difficulty ?? null,
        })),
      };

      if (quizMode === "create") {
        await api.post("/admin/quizzes", payload);
      } else {
        await api.put(`/admin/quizzes/${payload.id}`, payload);
      }

      await loadCatalog();
      setMessage(quizMode === "create" ? "Quiz created." : "Quiz updated.");
      resetQuizForm();
    } catch (error) {
      setMessage(`Could not save the quiz. ${summarizeError(error, "Make sure the questions JSON is valid.")}`);
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
              placeholder="Display name"
              value={moduleForm.display_name}
              onChange={(event) => {
                const display_name = event.target.value;
                setModuleForm((current) => ({
                  ...current,
                  display_name,
                }));
              }}
            />
            <p className="text-xs text-ink/55">Module id is generated automatically from the display name.</p>
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
              placeholder="Quiz display name"
              value={quizForm.display_name}
              onChange={(event) => {
                const display_name = event.target.value;
                setQuizForm((current) => ({
                  ...current,
                  display_name,
                }));
              }}
            />
            <p className="text-xs text-ink/55">Quiz id is generated automatically from the display name.</p>
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
